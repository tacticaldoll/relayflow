"""Execution nodes in the Session Graph: heterogeneous nodes + test-gated accept."""

from relayflow.artifact import ArtifactStore
from relayflow.demo import build_mixed_graph, marker_responder
from relayflow.executor import ExecResult, ExecSpec, MockExecutor
from relayflow.graph import BLOCKED, DONE, FAILED, SessionGraph, run_graph
from relayflow.llm import MockLLM
from relayflow.session import SessionContext, SessionInput
from relayflow.firewall import Budget


def llm():
    return MockLLM(responder=marker_responder)


def exec_result(files, status="passed"):
    return ExecResult(
        patch="--- a/src/x\n+++ b/src/x\n+y\n",
        summary="impl",
        tests="t",
        status=status,
        files=files,
    )


def exec_spec(node_id="impl", scope="g"):
    return ExecSpec(id=node_id, scope=scope, instruction="do", allowed_paths=["src/"])


def session(node_id, scope="g", inputs=None):
    return SessionInput(
        id=node_id,
        purpose="p",
        context=SessionContext(scope=scope, inputs=inputs or []),
        budget=Budget(100),
    )


# --- execution node basics -------------------------------------------------


def test_execution_node_writes_patch_and_test_edge_is_patch():
    store = ArtifactStore()
    graph = SessionGraph()
    ex = MockExecutor(result=exec_result(["src/x"]))
    graph.add_execution(exec_spec(), ex)
    result = run_graph(graph, store, llm())
    assert result.statuses["impl"] == DONE
    assert store.resolve("artifact://g/impl.patch").type == "patch"
    assert store.resolve("artifact://g/impl.test").metadata["status"] == "passed"


def test_session_depends_on_execution_patch_runs_after():
    store = ArtifactStore()
    graph = SessionGraph()
    ex = MockExecutor(result=exec_result(["src/x"]))
    graph.add_execution(exec_spec("impl"), ex)
    graph.add_node(session("review", inputs=["artifact://g/impl.patch"]))
    result = run_graph(graph, store, llm())
    assert ("impl", "review") in graph.edges()
    assert result.statuses == {"impl": DONE, "review": DONE}


# --- acceptance by tests ---------------------------------------------------


def test_failing_tests_fail_node_and_block_dependents():
    store = ArtifactStore()
    graph = SessionGraph()
    ex = MockExecutor(result=exec_result(["src/x"], status="failed"))
    graph.add_execution(exec_spec("impl"), ex)
    graph.add_node(session("review", inputs=["artifact://g/impl.patch"]))
    result = run_graph(graph, store, llm(), max_attempts=2)
    assert result.statuses["impl"] == FAILED
    assert result.statuses["review"] == BLOCKED


def test_file_scope_violation_is_not_accepted():
    store = ArtifactStore()
    graph = SessionGraph()
    ex = MockExecutor(result=exec_result(["src/x", "secrets.txt"]))
    graph.add_execution(exec_spec("impl"), ex)
    result = run_graph(graph, store, llm(), max_attempts=2)
    assert result.statuses["impl"] == FAILED
    # nothing propagated from the rejected attempt
    assert store.latest("g") == []


# --- mixed demo ------------------------------------------------------------


def test_mixed_graph_runs_to_done():
    store = ArtifactStore()
    graph = build_mixed_graph()
    result = run_graph(graph, store, llm())
    assert not result.failed and not result.blocked
    assert result.statuses == {"plan": DONE, "impl": DONE}
    assert store.resolve("artifact://mixed/impl.patch").type == "patch"
