"""Durable graph persistence + atomic node claim.

So a separate process (``relayflow run-node``) can load a node, run it, and
update its status, the graph's nodes/edges/status/attempts live in SQLite. The
runtime dependencies (llm, executor) are NOT persisted — only what to run (work
kind + spec + deps); how to run it is injected at load time.

Truth about *outputs* still lives in the artifact store; this store holds only
execution state (status/attempts) and the node definitions.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict

from relayflow.artifact import ArtifactStore
from relayflow.executor import ExecSpec, Executor
from relayflow.firewall import Budget, ContextPolicy
from relayflow.graph import (
    DONE,
    FAILED,
    PENDING,
    RUNNING,
    Acceptor,
    ExecutionWork,
    GraphNode,
    NodeWork,
    SessionGraph,
    SessionWork,
    accept_all,
)
from relayflow.llm import LLMClient
from relayflow.session import SessionContext, SessionInput, SessionStore


def _session_to_dict(session: SessionInput) -> dict:
    return asdict(session)


def _session_from_dict(d: dict) -> SessionInput:
    ctx = d["context"]
    context = SessionContext(
        scope=ctx["scope"],
        policy=ContextPolicy(**ctx["policy"]),
        inputs=list(ctx["inputs"]),
        preamble=ctx["preamble"],
        compression_threshold=ctx["compression_threshold"],
        summary_tokens=ctx["summary_tokens"],
    )
    return SessionInput(
        id=d["id"],
        purpose=d["purpose"],
        context=context,
        constraints=list(d["constraints"]),
        budget=Budget(**d["budget"]),
    )


def _serialize(work: NodeWork) -> tuple[str, dict, list[str]]:
    if isinstance(work, SessionWork):
        return "session", _session_to_dict(work.session), work.input_refs
    if isinstance(work, ExecutionWork):
        return "execution", asdict(work.spec), list(work.deps)
    raise TypeError(f"cannot serialize work {work!r}")


def _deserialize(
    kind: str, spec: dict, deps: list[str], executor: Executor | None
) -> NodeWork:
    if kind == "session":
        return SessionWork(session=_session_from_dict(spec))
    if kind == "execution":
        # executor may be None for read-only rendering (inspect); it is only
        # required to actually run the node.
        return ExecutionWork(spec=ExecSpec(**spec), executor=executor, deps=deps)
    raise ValueError(f"unknown work kind {kind!r}")


class GraphStore:
    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS graph_nodes (
                graph_id              TEXT NOT NULL,
                node_id               TEXT NOT NULL,
                kind                  TEXT NOT NULL,
                spec                  TEXT NOT NULL,
                deps                  TEXT NOT NULL,
                status                TEXT NOT NULL,
                attempts              INTEGER NOT NULL,
                requires_confirmation INTEGER NOT NULL,
                PRIMARY KEY (graph_id, node_id)
            )
            """
        )
        self._conn.commit()

    def save_graph(self, graph_id: str, graph: SessionGraph) -> None:
        for node in graph.nodes.values():
            kind, spec, deps = _serialize(node.work)
            self._conn.execute(
                "INSERT OR REPLACE INTO graph_nodes "
                "(graph_id, node_id, kind, spec, deps, status, attempts, "
                "requires_confirmation) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    graph_id,
                    node.id,
                    kind,
                    json.dumps(spec),
                    json.dumps(deps),
                    node.status,
                    node.attempts,
                    int(node.requires_confirmation),
                ),
            )
        self._conn.commit()

    def load_graph(
        self, graph_id: str, *, executor: Executor | None = None
    ) -> SessionGraph:
        rows = self._conn.execute(
            "SELECT node_id, kind, spec, deps, status, attempts, "
            "requires_confirmation FROM graph_nodes WHERE graph_id = ?",
            (graph_id,),
        ).fetchall()
        graph = SessionGraph()
        for row in rows:
            work = _deserialize(
                row["kind"], json.loads(row["spec"]), json.loads(row["deps"]), executor
            )
            graph.nodes[row["node_id"]] = GraphNode(
                work=work,
                status=row["status"],
                attempts=row["attempts"],
                requires_confirmation=bool(row["requires_confirmation"]),
            )
        return graph

    def exists(self, graph_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM graph_nodes WHERE graph_id = ? LIMIT 1", (graph_id,)
        ).fetchone()
        return row is not None

    def get_status(self, graph_id: str, node_id: str) -> tuple[str, int]:
        row = self._conn.execute(
            "SELECT status, attempts FROM graph_nodes WHERE graph_id=? AND node_id=?",
            (graph_id, node_id),
        ).fetchone()
        if row is None:
            raise KeyError(f"{graph_id}/{node_id}")
        return row["status"], row["attempts"]

    def update_status(
        self, graph_id: str, node_id: str, status: str, attempts: int | None = None
    ) -> None:
        if attempts is None:
            self._conn.execute(
                "UPDATE graph_nodes SET status=? WHERE graph_id=? AND node_id=?",
                (status, graph_id, node_id),
            )
        else:
            self._conn.execute(
                "UPDATE graph_nodes SET status=?, attempts=? "
                "WHERE graph_id=? AND node_id=?",
                (status, attempts, graph_id, node_id),
            )
        self._conn.commit()

    def claim(self, graph_id: str, node_id: str) -> bool:
        """Atomic CAS: pending -> running. True iff this caller won the claim."""
        cur = self._conn.execute(
            "UPDATE graph_nodes SET status=? "
            "WHERE graph_id=? AND node_id=? AND status=?",
            (RUNNING, graph_id, node_id, PENDING),
        )
        self._conn.commit()
        return cur.rowcount == 1


def run_node(
    gstore: GraphStore,
    graph_id: str,
    node_id: str,
    artifacts: ArtifactStore,
    *,
    llm: LLMClient | None = None,
    executor: Executor | None = None,
    acceptor: Acceptor = accept_all,
    sessions: SessionStore | None = None,
) -> str:
    """Idempotently run one persisted node. Returns its outcome.

    ``"noop"`` if already done, ``"skipped"`` if the claim was lost (another
    runner has it), else ``"done"`` / ``"failed"``. Idempotency rests on the
    CAS-claim plus truth living in the artifact store.
    """
    status, _ = gstore.get_status(graph_id, node_id)
    if status == DONE:
        return "noop"
    if not gstore.claim(graph_id, node_id):
        return "skipped"

    graph = gstore.load_graph(graph_id, executor=executor)
    node = graph.nodes[node_id]
    ran = node.work.run(artifacts, llm=llm, executor=executor, sessions=sessions)
    if ran and node.work.accepted(artifacts, acceptor):
        gstore.update_status(graph_id, node_id, DONE)
        return DONE
    gstore.update_status(graph_id, node_id, FAILED)
    return FAILED
