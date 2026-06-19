"""Session Graph: sessions and executions as nodes, artifacts as edges.

The graph generalizes V0's linear relay to a DAG. A node wraps a unit of *work*
(a session or an execution); the scheduler is work-agnostic. A node is ready only
when all of its input artifacts exist and are accepted; the ready set is
recomputed from graph + artifact state each tick rather than stored. An
acceptance gate stops a bad artifact from propagating: a rejected artifact
regenerates its node up to a bounded number of attempts, and dependents stay
blocked until inputs are accepted.

Synchronous and single-process by design — concurrency, retries-as-jobs, and any
execution substrate (worklane) are a separate, later change.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from relayflow.artifact import Artifact, ArtifactNotFound, ArtifactStore
from relayflow.broker import Broker, InMemoryBroker
from relayflow.events import (
    APPROVAL_DENIED,
    APPROVAL_GRANTED,
    APPROVAL_REQUIRED,
    NODE_BLOCKED,
    NODE_DONE,
    NODE_FAILED,
    Event,
    EventBus,
)
from relayflow.executor import ExecSpec, Executor, FileScopeViolation, run_execution
from relayflow.llm import LLMClient
from relayflow.session import SessionInput, SessionStore, run_session

Approver = Callable[["GraphNode"], bool]

PENDING = "pending"
READY = "ready"
RUNNING = "running"
DONE = "done"
BLOCKED = "blocked"
FAILED = "failed"

Acceptor = Callable[[Artifact], bool]


def accept_all(_artifact: Artifact) -> bool:
    return True


@runtime_checkable
class NodeWork(Protocol):
    """A unit of graph work: produces a primary output artifact and is judged."""

    @property
    def id(self) -> str: ...

    @property
    def scope(self) -> str: ...

    @property
    def input_refs(self) -> list[str]: ...

    @property
    def output_ref(self) -> str: ...

    def run(
        self,
        store: ArtifactStore,
        *,
        llm: LLMClient | None,
        executor: Executor | None,
        sessions: SessionStore | None,
    ) -> bool:
        """Run the work once. Return False if the attempt failed structurally."""

    def accepted(self, store: ArtifactStore, acceptor: Acceptor) -> bool:
        """Whether this node's produced output is accepted."""


@dataclass
class SessionWork:
    session: SessionInput

    @property
    def id(self) -> str:
        return self.session.id

    @property
    def scope(self) -> str:
        return self.session.context.scope

    @property
    def input_refs(self) -> list[str]:
        return list(self.session.context.inputs)

    @property
    def output_ref(self) -> str:
        return f"artifact://{self.scope}/{self.id}.out"

    def run(self, store, *, llm, executor, sessions) -> bool:
        if llm is None:
            raise ValueError(f"session node {self.id!r} requires an llm")
        run_session(store, llm, self.session, sessions)
        return True

    def accepted(self, store, acceptor) -> bool:
        return acceptor(store.resolve(self.output_ref))


@dataclass
class ExecutionWork:
    spec: ExecSpec
    executor: Executor
    deps: list[str]

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def scope(self) -> str:
        return self.spec.scope

    @property
    def input_refs(self) -> list[str]:
        return list(self.deps)

    @property
    def output_ref(self) -> str:
        return f"artifact://{self.scope}/{self.id}.patch"

    @property
    def test_ref(self) -> str:
        return f"artifact://{self.scope}/{self.id}.test"

    def run(self, store, *, llm, executor, sessions) -> bool:
        worker = executor if executor is not None else self.executor
        try:
            run_execution(store, worker, self.spec)
        except FileScopeViolation:
            return False
        return True

    def accepted(self, store, acceptor) -> bool:
        try:
            test = store.resolve(self.test_ref)
        except ArtifactNotFound:
            return False
        return test.metadata.get("status") == "passed"


@dataclass
class GraphNode:
    work: NodeWork
    status: str = PENDING
    attempts: int = 0
    requires_confirmation: bool = False

    @property
    def id(self) -> str:
        return self.work.id

    @property
    def output_ref(self) -> str:
        return self.work.output_ref

    @property
    def input_refs(self) -> list[str]:
        return self.work.input_refs


@dataclass
class GraphRunResult:
    statuses: dict[str, str]
    completed: list[str]
    failed: list[str]
    blocked: list[str]


class SessionGraph:
    """A DAG of work nodes. Edges are derived from input references."""

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}

    def add_node(
        self, session: SessionInput, *, requires_confirmation: bool = False
    ) -> GraphNode:
        return self._add(
            SessionWork(session=session), requires_confirmation=requires_confirmation
        )

    def add_execution(
        self,
        spec: ExecSpec,
        executor: Executor,
        deps: list[str] | None = None,
        *,
        requires_confirmation: bool = False,
    ) -> GraphNode:
        return self._add(
            ExecutionWork(spec=spec, executor=executor, deps=deps or []),
            requires_confirmation=requires_confirmation,
        )

    def _add(self, work: NodeWork, *, requires_confirmation: bool = False) -> GraphNode:
        node = GraphNode(work=work, requires_confirmation=requires_confirmation)
        self.nodes[node.id] = node
        return node

    def producer_of(self, ref: str) -> GraphNode | None:
        for node in self.nodes.values():
            if node.output_ref == ref:
                return node
        return None

    def dependencies(self, node: GraphNode) -> list[GraphNode]:
        deps = []
        for ref in node.input_refs:
            producer = self.producer_of(ref)
            if producer is not None:
                deps.append(producer)
        return deps

    def roots(self) -> list[GraphNode]:
        return [n for n in self.nodes.values() if not self.dependencies(n)]

    def edges(self) -> list[tuple[str, str]]:
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
            if not _exists(store, ref):
                return False
        else:
            if producer.status != DONE or ref not in accepted:
                return False
    return True


def _emit(events: EventBus | None, event_type: str, node_id: str) -> None:
    if events is not None:
        events.emit(Event(type=event_type, payload={"node": node_id}))


def drive(
    graph: SessionGraph,
    artifacts: ArtifactStore,
    broker: Broker,
    *,
    llm: LLMClient | None = None,
    acceptor: Acceptor = accept_all,
    max_attempts: int = 1,
    sessions: SessionStore | None = None,
    executor: Executor | None = None,
    events: EventBus | None = None,
    approver: Approver | None = None,
) -> GraphRunResult:
    """Drive a graph over a broker: enqueue ready nodes, reserve, run, repeat.

    Readiness stays a projection of graph + artifact state. A ready confirmation
    node is parked (not enqueued) until approved. A rejected node is retried via
    the broker up to ``max_attempts``, then dead-lettered and marked ``failed``.
    """
    accepted: set[str] = set()
    inflight: set[str] = set()

    def claim(node: GraphNode) -> bool:
        if node.status == PENDING:
            node.status = RUNNING
            return True
        return False

    def try_enqueue(node: GraphNode) -> None:
        if node.status != PENDING or node.id in inflight:
            return
        if not _ready(graph, node, artifacts, accepted):
            return
        if node.requires_confirmation:
            _emit(events, APPROVAL_REQUIRED, node.id)
            if approver is None or not approver(node):
                _emit(events, APPROVAL_DENIED, node.id)
                node.status = BLOCKED
                _emit(events, NODE_BLOCKED, node.id)
                return
            _emit(events, APPROVAL_GRANTED, node.id)
        broker.enqueue({"node_id": node.id}, unique_key=node.id)
        inflight.add(node.id)

    for node in graph.nodes.values():
        try_enqueue(node)

    while True:
        job = broker.reserve()
        if job is None:
            break
        node = graph.nodes[job.payload["node_id"]]
        if not claim(node):
            broker.ack(job)
            continue
        node.attempts += 1
        ran = node.work.run(artifacts, llm=llm, executor=executor, sessions=sessions)
        if ran and node.work.accepted(artifacts, acceptor):
            node.status = DONE
            accepted.add(node.output_ref)
            _emit(events, NODE_DONE, node.id)
            broker.ack(job)
        elif node.attempts < max_attempts:
            node.status = PENDING  # claimable again for the retry delivery
            broker.retry(job)
        else:
            node.status = FAILED
            _emit(events, NODE_FAILED, node.id)
            broker.dead_letter(job)
        for other in graph.nodes.values():
            try_enqueue(other)

    for node in graph.nodes.values():
        if node.status not in (DONE, FAILED, BLOCKED):
            node.status = BLOCKED
            _emit(events, NODE_BLOCKED, node.id)

    return GraphRunResult(
        statuses={n.id: n.status for n in graph.nodes.values()},
        completed=[n.id for n in graph.nodes.values() if n.status == DONE],
        failed=[n.id for n in graph.nodes.values() if n.status == FAILED],
        blocked=[n.id for n in graph.nodes.values() if n.status == BLOCKED],
    )


def run_graph(
    graph: SessionGraph,
    artifacts: ArtifactStore,
    llm: LLMClient | None = None,
    *,
    acceptor: Acceptor = accept_all,
    max_attempts: int = 1,
    sessions: SessionStore | None = None,
    executor: Executor | None = None,
    events: EventBus | None = None,
    approver: Approver | None = None,
) -> GraphRunResult:
    """Synchronous run: drive the graph over an in-memory broker to a fixed point.

    This is the shared path — the same ``drive`` loop a durable broker uses, with
    an in-memory broker standing in for the queue.
    """
    return drive(
        graph,
        artifacts,
        InMemoryBroker(),
        llm=llm,
        acceptor=acceptor,
        max_attempts=max_attempts,
        sessions=sessions,
        executor=executor,
        events=events,
        approver=approver,
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
