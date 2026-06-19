from relayflow.artifact import ArtifactStore
from relayflow.demo import MarkerRelayTask, build_marker_graph, marker_responder
from relayflow.executor import ExecResult, ExecSpec, MockExecutor
from relayflow.firewall import Budget, ContextPolicy
from relayflow.graph import DONE, RUNNING, SessionGraph
from relayflow.graphstore import GraphStore, run_node
from relayflow.llm import MockLLM
from relayflow.session import SessionContext, SessionInput


def llm():
    return MockLLM(responder=marker_responder)


def session(node_id, scope="g", inputs=None):
    return SessionInput(
        id=node_id,
        purpose="p",
        context=SessionContext(
            scope=scope, policy=ContextPolicy("latest"), inputs=inputs or []
        ),
        budget=Budget(100),
    )


# --- persistence -----------------------------------------------------------


def test_graph_round_trips_through_store():
    graph = SessionGraph()
    graph.add_node(session("a"))
    graph.add_node(session("b", inputs=["artifact://g/a.out"]))
    gs = GraphStore()
    gs.save_graph("G", graph)

    loaded = gs.load_graph("G")
    assert set(loaded.nodes) == {"a", "b"}
    assert ("a", "b") in loaded.edges()
    assert loaded.nodes["a"].status == "pending"
    assert loaded.nodes["b"].input_refs == ["artifact://g/a.out"]


def test_execution_node_round_trips_with_injected_executor():
    graph = SessionGraph()
    ex = MockExecutor(
        result=ExecResult(patch="p", summary="s", tests="t", status="passed", files=[])
    )
    graph.add_execution(ExecSpec(id="impl", scope="g", instruction="do"), ex)
    gs = GraphStore()
    gs.save_graph("G", graph)

    loaded = gs.load_graph("G", executor=ex)
    assert loaded.nodes["impl"].output_ref == "artifact://g/impl.patch"


def test_status_update_is_durable():
    graph = SessionGraph()
    graph.add_node(session("a"))
    gs = GraphStore()
    gs.save_graph("G", graph)
    gs.update_status("G", "a", DONE, attempts=3)
    assert gs.get_status("G", "a") == (DONE, 3)
    assert gs.load_graph("G").nodes["a"].status == DONE


# --- CAS-claim & idempotency ----------------------------------------------


def test_concurrent_claims_yield_single_winner():
    graph = SessionGraph()
    graph.add_node(session("a"))
    gs = GraphStore()
    gs.save_graph("G", graph)
    assert gs.claim("G", "a") is True
    assert gs.claim("G", "a") is False  # already running
    assert gs.get_status("G", "a")[0] == RUNNING


def test_run_node_then_duplicate_delivery_is_noop():
    store = ArtifactStore()
    task = MarkerRelayTask()
    task.setup(store)
    graph = build_marker_graph(task, Budget(60))
    gs = GraphStore()
    gs.save_graph("demo", graph)

    first = run_node(gs, "demo", "extract0", store, llm=llm())
    second = run_node(gs, "demo", "extract0", store, llm=llm())
    assert first == DONE
    assert second == "noop"
    assert store.resolve("artifact://demo/extract0.out") is not None
