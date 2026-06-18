from relayflow.artifact import ArtifactStore
from relayflow.demo import MarkerRelayTask, build_marker_graph, marker_responder
from relayflow.firewall import Budget
from relayflow.graph import (
    BLOCKED,
    DONE,
    FAILED,
    PENDING,
    SessionGraph,
    run_graph,
    visualize,
)
from relayflow.llm import MockLLM
from relayflow.session import SessionContext, SessionInput

BUDGET = 60


def llm():
    return MockLLM(responder=marker_responder)


def node_input(node_id, scope="g", inputs=None):
    return SessionInput(
        id=node_id,
        purpose="work",
        context=SessionContext(scope=scope, inputs=inputs or []),
        budget=Budget(BUDGET),
    )


# --- model -----------------------------------------------------------------


def test_node_starts_pending_and_roots_identified():
    graph = SessionGraph()
    a = graph.add_node(node_input("a"))
    graph.add_node(node_input("b", inputs=["artifact://g/a.out"]))
    assert a.status == PENDING
    assert [n.id for n in graph.roots()] == ["a"]


def test_edges_link_producer_to_consumer():
    graph = SessionGraph()
    graph.add_node(node_input("a"))
    graph.add_node(node_input("b", inputs=["artifact://g/a.out"]))
    assert ("a", "b") in graph.edges()


# --- scheduler -------------------------------------------------------------


def test_linear_chain_runs_in_order_all_done():
    store = ArtifactStore()
    graph = SessionGraph()
    graph.add_node(node_input("a", inputs=[]))
    graph.add_node(node_input("b", inputs=["artifact://g/a.out"]))
    result = run_graph(graph, store, llm())
    assert result.statuses == {"a": DONE, "b": DONE}


def test_diamond_graph_completes_in_dependency_order():
    store = ArtifactStore()
    graph = SessionGraph()
    graph.add_node(node_input("root", inputs=[]))
    graph.add_node(node_input("m1", inputs=["artifact://g/root.out"]))
    graph.add_node(node_input("m2", inputs=["artifact://g/root.out"]))
    graph.add_node(
        node_input("sink", inputs=["artifact://g/m1.out", "artifact://g/m2.out"])
    )
    result = run_graph(graph, store, llm())
    assert set(result.completed) == {"root", "m1", "m2", "sink"}
    assert result.statuses["sink"] == DONE


def test_node_with_unaccepted_input_does_not_run():
    store = ArtifactStore()
    graph = SessionGraph()
    graph.add_node(node_input("a", inputs=[]))
    graph.add_node(node_input("b", inputs=["artifact://g/a.out"]))

    reject_a = lambda art: art.id != "a.out"  # noqa: E731
    result = run_graph(graph, store, llm(), acceptor=reject_a, max_attempts=2)
    assert result.statuses["a"] == FAILED
    assert result.statuses["b"] == BLOCKED


# --- acceptance gate -------------------------------------------------------


def test_rejected_artifact_regenerates_then_accepts():
    store = ArtifactStore()
    graph = SessionGraph()
    graph.add_node(node_input("a", inputs=[]))

    attempts = {"n": 0}

    def accept_on_second(_art):
        attempts["n"] += 1
        return attempts["n"] >= 2

    result = run_graph(graph, store, llm(), acceptor=accept_on_second, max_attempts=3)
    assert result.statuses["a"] == DONE
    assert graph.nodes["a"].attempts == 2


def test_exhausted_attempts_fail_node_and_block_dependents():
    store = ArtifactStore()
    graph = SessionGraph()
    graph.add_node(node_input("a", inputs=[]))
    graph.add_node(node_input("b", inputs=["artifact://g/a.out"]))
    result = run_graph(graph, store, llm(), acceptor=lambda _a: False, max_attempts=2)
    assert result.statuses["a"] == FAILED
    assert result.statuses["b"] == BLOCKED
    assert graph.nodes["a"].attempts == 2


# --- construction & visualization -----------------------------------------


def test_nodes_added_explicitly_without_model_planning():
    graph = SessionGraph()
    graph.add_node(node_input("a"))
    # no LLM was constructed or called to plan the graph
    assert list(graph.nodes) == ["a"]


def test_visualizer_lists_nodes_status_and_edges():
    task = MarkerRelayTask()
    store = ArtifactStore()
    task.setup(store)
    graph = build_marker_graph(task, Budget(BUDGET))
    run_graph(graph, store, llm())
    text = visualize(graph)
    assert "synthesis [done]" in text
    assert "extract0 -> synthesis" in text


# --- end to end ------------------------------------------------------------


def test_demo_graph_runs_to_done_and_synthesis_is_complete():
    task = MarkerRelayTask()
    store = ArtifactStore()
    task.setup(store)
    graph = build_marker_graph(task, Budget(BUDGET))
    result = run_graph(graph, store, llm())

    assert not result.failed and not result.blocked
    final = store.resolve("artifact://demo/synthesis.out").content
    assert len(final.split()) == task.total_facts


def test_external_seeded_inputs_are_treated_as_satisfied():
    # extract nodes depend on seeded group sources (external, not node-produced)
    task = MarkerRelayTask()
    store = ArtifactStore()
    task.setup(store)
    graph = build_marker_graph(task, Budget(BUDGET))
    # roots are the extract nodes (their inputs are external seeded artifacts)
    assert {n.id for n in graph.roots()} == {f"extract{g}" for g in range(4)}
    result = run_graph(graph, store, llm())
    assert result.statuses["extract0"] == DONE
