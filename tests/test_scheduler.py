"""Broker-driven scheduler: newly-ready enqueue, retry-as-jobs, parked approval."""

from relayflow.artifact import ArtifactStore
from relayflow.broker import InMemoryBroker
from relayflow.demo import marker_responder
from relayflow.firewall import Budget
from relayflow.graph import BLOCKED, DONE, FAILED, SessionGraph, drive
from relayflow.llm import MockLLM
from relayflow.session import SessionContext, SessionInput


def llm():
    return MockLLM(responder=marker_responder)


def session(node_id, scope="g", inputs=None):
    return SessionInput(
        id=node_id,
        purpose="p",
        context=SessionContext(scope=scope, inputs=inputs or []),
        budget=Budget(100),
    )


def test_completing_a_node_enqueues_only_newly_ready_dependents():
    # diamond: root -> m1,m2 -> sink; each node runs exactly once (attempts==1)
    store = ArtifactStore()
    graph = SessionGraph()
    graph.add_node(session("root"))
    graph.add_node(session("m1", inputs=["artifact://g/root.out"]))
    graph.add_node(session("m2", inputs=["artifact://g/root.out"]))
    graph.add_node(
        session("sink", inputs=["artifact://g/m1.out", "artifact://g/m2.out"])
    )
    result = drive(graph, store, InMemoryBroker(), llm=llm())
    assert set(result.completed) == {"root", "m1", "m2", "sink"}
    assert all(n.attempts == 1 for n in graph.nodes.values())  # no duplicate runs


def test_retry_then_accept_via_broker():
    store = ArtifactStore()
    graph = SessionGraph()
    graph.add_node(session("a"))
    attempts = {"n": 0}

    def accept_on_second(_art):
        attempts["n"] += 1
        return attempts["n"] >= 2

    result = drive(
        graph,
        store,
        InMemoryBroker(),
        llm=llm(),
        acceptor=accept_on_second,
        max_attempts=3,
    )
    assert result.statuses["a"] == DONE
    assert graph.nodes["a"].attempts == 2


def test_exhausted_retries_dead_letter_and_fail():
    store = ArtifactStore()
    broker = InMemoryBroker()
    graph = SessionGraph()
    graph.add_node(session("a"))
    graph.add_node(session("b", inputs=["artifact://g/a.out"]))
    result = drive(
        graph, store, broker, llm=llm(), acceptor=lambda _a: False, max_attempts=2
    )
    assert result.statuses["a"] == FAILED
    assert result.statuses["b"] == BLOCKED
    assert len(broker.dead) == 1  # the failed node's job was dead-lettered


def test_parked_approval_enqueues_only_when_approved():
    store = ArtifactStore()
    graph = SessionGraph()
    graph.add_node(session("gate"), requires_confirmation=True)
    # denied: parked, never run
    denied = drive(graph, store, InMemoryBroker(), llm=llm(), approver=lambda n: False)
    assert denied.statuses["gate"] == BLOCKED

    # fresh graph, approved: runs
    graph2 = SessionGraph()
    graph2.add_node(session("gate"), requires_confirmation=True)
    granted = drive(graph2, store, InMemoryBroker(), llm=llm(), approver=lambda n: True)
    assert granted.statuses["gate"] == DONE
