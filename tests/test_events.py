"""Event bus + human approval gating in the graph."""

from relayflow.artifact import ArtifactStore
from relayflow.demo import build_approval_graph, marker_responder
from relayflow.events import (
    APPROVAL_DENIED,
    APPROVAL_GRANTED,
    APPROVAL_REQUIRED,
    NODE_DONE,
    Event,
    InMemoryBus,
)
from relayflow.firewall import Budget
from relayflow.graph import BLOCKED, DONE, SessionGraph, run_graph
from relayflow.llm import MockLLM
from relayflow.session import SessionContext, SessionInput


def llm():
    return MockLLM(responder=marker_responder)


def session(node_id, inputs=None, scope="g"):
    return SessionInput(
        id=node_id,
        purpose="p",
        context=SessionContext(scope=scope, inputs=inputs or []),
        budget=Budget(100),
    )


# --- event bus -------------------------------------------------------------


def test_subscribed_listener_receives_emitted_events():
    bus = InMemoryBus()
    seen = []
    bus.subscribe(seen.append)
    bus.emit(Event(type="x", payload={"a": 1}))
    assert seen == [Event(type="x", payload={"a": 1})]
    assert bus.types() == ["x"]


def test_listener_receives_externally_injected_event():
    bus = InMemoryBus()
    seen = []
    bus.subscribe(seen.append)
    bus.receive(Event(type="report", payload={}))
    assert [e.type for e in seen] == ["report"]


# --- lifecycle emission ----------------------------------------------------


def test_run_emits_node_done_events():
    bus = InMemoryBus()
    graph = SessionGraph()
    graph.add_node(session("a"))
    run_graph(graph, ArtifactStore(), llm(), events=bus)
    assert NODE_DONE in bus.types()


def test_run_without_bus_behaves_unchanged():
    graph = SessionGraph()
    graph.add_node(session("a"))
    result = run_graph(graph, ArtifactStore(), llm())
    assert result.statuses == {"a": DONE}


# --- human approval --------------------------------------------------------


def test_approved_node_runs():
    bus = InMemoryBus()
    graph = SessionGraph()
    graph.add_node(session("a"), requires_confirmation=True)
    result = run_graph(
        graph, ArtifactStore(), llm(), events=bus, approver=lambda n: True
    )
    assert result.statuses["a"] == DONE
    assert APPROVAL_REQUIRED in bus.types()
    assert APPROVAL_GRANTED in bus.types()


def test_denied_node_does_not_run_and_blocks_dependents():
    bus = InMemoryBus()
    graph = SessionGraph()
    graph.add_node(session("a"), requires_confirmation=True)
    graph.add_node(session("b", inputs=["artifact://g/a.out"]))
    result = run_graph(
        graph, ArtifactStore(), llm(), events=bus, approver=lambda n: False
    )
    assert result.statuses["a"] == BLOCKED
    assert result.statuses["b"] == BLOCKED
    assert APPROVAL_DENIED in bus.types()
    # the gated node never produced its artifact
    assert ArtifactStore().latest("g") == []


def test_requires_confirmation_without_approver_is_blocked():
    graph = SessionGraph()
    graph.add_node(session("a"), requires_confirmation=True)
    result = run_graph(graph, ArtifactStore(), llm())
    assert result.statuses["a"] == BLOCKED


# --- demo ------------------------------------------------------------------


def test_approval_demo_graph_runs_with_auto_approver():
    from relayflow.demo import auto_approver

    bus = InMemoryBus()
    graph = build_approval_graph()
    result = run_graph(
        graph,
        ArtifactStore(),
        llm(),
        events=bus,
        approver=auto_approver,
    )
    assert result.statuses == {"plan": DONE, "deploy": DONE}
    assert APPROVAL_REQUIRED in bus.types()
