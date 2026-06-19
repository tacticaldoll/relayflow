from relayflow.artifact import ArtifactStore
from relayflow.demo import build_mixed_graph, marker_responder
from relayflow.executor import ExecResult, ExecSpec, MockExecutor
from relayflow.graph import SessionGraph, run_graph, visualize
from relayflow.graphstore import GraphStore
from relayflow.llm import MockLLM
from relayflow.session import SessionContext, SessionInput
from relayflow.firewall import Budget


def llm():
    return MockLLM(responder=marker_responder)


def test_visualize_shows_kind_and_edge_artifact():
    graph = build_mixed_graph()
    run_graph(graph, ArtifactStore(), llm())
    text = visualize(graph)
    assert "plan [done] (session)" in text
    assert "impl [done] (execution)" in text
    assert "plan -> impl  [artifact://mixed/plan.out]" in text
    assert "summary:" in text


def test_visualize_status_summary_counts():
    graph = SessionGraph()
    graph.add_node(
        SessionInput(
            id="a", purpose="p", context=SessionContext(scope="g"), budget=Budget(50)
        )
    )
    run_graph(graph, ArtifactStore(), llm())
    assert "1 nodes (done=1)" in visualize(graph)


def test_load_execution_graph_without_executor_renders():
    graph = SessionGraph()
    ex = MockExecutor(
        result=ExecResult(patch="p", summary="s", tests="t", status="passed", files=[])
    )
    graph.add_execution(ExecSpec(id="impl", scope="g", instruction="do"), ex)
    gs = GraphStore()
    gs.save_graph("G", graph)

    loaded = gs.load_graph("G")  # no executor — read-only render path
    text = visualize(loaded)
    assert "impl [pending] (execution)" in text


def test_graphstore_exists():
    gs = GraphStore()
    assert gs.exists("G") is False
    graph = SessionGraph()
    graph.add_node(
        SessionInput(
            id="a", purpose="p", context=SessionContext(scope="g"), budget=Budget(50)
        )
    )
    gs.save_graph("G", graph)
    assert gs.exists("G") is True
