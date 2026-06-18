"""Session Graph: sessions as nodes, artifacts as edges, advanced by a scheduler.

The graph generalizes V0's linear relay to a DAG. A node is ready only when all
of its input artifacts exist and are accepted; the ready set is recomputed from
graph + artifact state each tick rather than stored. An acceptance gate stops a
bad artifact from propagating: a rejected artifact regenerates its node up to a
bounded number of attempts, and dependents stay blocked until inputs are accepted.

This is synchronous and single-process by design — concurrency, retries-as-jobs,
and any execution substrate (worklane) are a separate, later change.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from relayflow.artifact import Artifact, ArtifactNotFound, ArtifactStore
from relayflow.llm import LLMClient
from relayflow.session import SessionInput, SessionStore, run_session

PENDING = "pending"
READY = "ready"
RUNNING = "running"
DONE = "done"
BLOCKED = "blocked"
FAILED = "failed"

Acceptor = Callable[[Artifact], bool]


def accept_all(_artifact: Artifact) -> bool:
    return True


@dataclass
class GraphNode:
    session: SessionInput
    status: str = PENDING
    attempts: int = 0

    @property
    def id(self) -> str:
        return self.session.id

    @property
    def output_ref(self) -> str:
        return f"artifact://{self.session.context.scope}/{self.session.id}.out"

    @property
    def input_refs(self) -> list[str]:
        return list(self.session.context.inputs)


@dataclass
class GraphRunResult:
    statuses: dict[str, str]
    completed: list[str]
    failed: list[str]
    blocked: list[str]


class SessionGraph:
    """A DAG of session nodes. Edges are derived from input references."""

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}

    def add_node(self, session: SessionInput) -> GraphNode:
        node = GraphNode(session=session)
        self.nodes[node.id] = node
        return node

    def producer_of(self, ref: str) -> GraphNode | None:
        for node in self.nodes.values():
            if node.output_ref == ref:
                return node
        return None

    def dependencies(self, node: GraphNode) -> list[GraphNode]:
        """Producer nodes this node depends on (external refs are not nodes)."""
        deps = []
        for ref in node.input_refs:
            producer = self.producer_of(ref)
            if producer is not None:
                deps.append(producer)
        return deps

    def roots(self) -> list[GraphNode]:
        return [n for n in self.nodes.values() if not self.dependencies(n)]

    def edges(self) -> list[tuple[str, str]]:
        """(producer_id, consumer_id) pairs."""
        result = []
        for node in self.nodes.values():
            for dep in self.dependencies(node):
                result.append((dep.id, node.id))
        return result


def _exists(store: ArtifactStore, ref: str) -> bool:
    try:
        store.resolve(ref)
        return True
    except ArtifactNotFound:
        return False


def _ready(
    graph: SessionGraph,
    node: GraphNode,
    store: ArtifactStore,
    accepted: set[str],
) -> bool:
    for ref in node.input_refs:
        producer = graph.producer_of(ref)
        if producer is None:
            # external (seeded) input: satisfied if it exists in the store
            if not _exists(store, ref):
                return False
        else:
            # internal input: producer must be done and its artifact accepted
            if producer.status != DONE or ref not in accepted:
                return False
    return True


def run_graph(
    graph: SessionGraph,
    artifacts: ArtifactStore,
    llm: LLMClient,
    *,
    acceptor: Acceptor = accept_all,
    max_attempts: int = 1,
    sessions: SessionStore | None = None,
) -> GraphRunResult:
    """Run the graph to a fixed point: run ready nodes until none remain ready."""
    accepted: set[str] = set()

    progressed = True
    while progressed:
        progressed = False
        for node in graph.nodes.values():
            if node.status in (DONE, FAILED):
                continue
            if not _ready(graph, node, artifacts, accepted):
                continue

            node.status = RUNNING
            ok = False
            while node.attempts < max_attempts:
                node.attempts += 1
                run_session(artifacts, llm, node.session, sessions)
                produced = artifacts.resolve(node.output_ref)
                if acceptor(produced):
                    accepted.add(node.output_ref)
                    ok = True
                    break
            node.status = DONE if ok else FAILED
            progressed = True

    # Anything not done/failed could never become ready: it is blocked.
    for node in graph.nodes.values():
        if node.status not in (DONE, FAILED):
            node.status = BLOCKED

    return GraphRunResult(
        statuses={n.id: n.status for n in graph.nodes.values()},
        completed=[n.id for n in graph.nodes.values() if n.status == DONE],
        failed=[n.id for n in graph.nodes.values() if n.status == FAILED],
        blocked=[n.id for n in graph.nodes.values() if n.status == BLOCKED],
    )


def visualize(graph: SessionGraph) -> str:
    """Render the graph as readable text: nodes with status, then edges."""
    lines = ["nodes:"]
    for node in graph.nodes.values():
        lines.append(f"  {node.id} [{node.status}]")
    lines.append("edges:")
    for producer, consumer in graph.edges():
        lines.append(f"  {producer} -> {consumer}")
    return "\n".join(lines)
