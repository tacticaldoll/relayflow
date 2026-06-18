"""End-to-end PoC: the relay closes the loop and the bet holds."""

from relayflow.artifact import ArtifactStore
from relayflow.demo import MarkerRelayTask, marker_responder
from relayflow.falsification import run_experiment_matrix, run_task
from relayflow.firewall import Budget
from relayflow.llm import MockLLM
from relayflow.session import SessionStore

BUDGET = 60


def test_v0_poc_relay_closes_loop_and_bet_holds(tmp_path):
    task = MarkerRelayTask()
    artifacts = ArtifactStore(str(tmp_path / "store.db"))
    task.setup(artifacts)
    sessions = SessionStore(str(tmp_path / "store.db"))
    llm = MockLLM(responder=marker_responder)

    # relay-on run produces the full artifact chain and completes
    report = run_task(
        artifacts, llm, task, relay=True, budget=Budget(BUDGET), sessions=sessions
    )
    assert report.acceptance == "complete"
    assert report.peak_session_tokens <= BUDGET

    # every relayed session is persisted and inspectable as a trace
    for sid in ["extract0", "extract1", "extract2", "extract3", "synthesis"]:
        record = sessions.get(sid)
        assert record.artifacts == [f"artifact://demo/{sid}.out"]

    # the synthesis artifact carries every marker — work advanced to completion
    final = artifacts.resolve("artifact://demo/synthesis.out").content
    assert len(final.split()) == task.total_facts


def test_v0_poc_headline_metric():
    # peak_session_tokens <= budget < single_shot_tokens, relay-on completes
    matrix = run_experiment_matrix(
        MarkerRelayTask(), MockLLM(responder=marker_responder), BUDGET
    )
    assert matrix.bet_holds
    assert (
        matrix.relay_on_bounded.peak_session_tokens
        <= matrix.budget
        < matrix.single_shot_tokens
    )
