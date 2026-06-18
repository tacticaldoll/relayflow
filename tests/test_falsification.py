from relayflow.artifact import ArtifactStore
from relayflow.demo import MarkerRelayTask, marker_responder
from relayflow.falsification import run_experiment_matrix, run_task
from relayflow.firewall import Budget
from relayflow.llm import MockLLM

BUDGET = 60


def llm():
    return MockLLM(responder=marker_responder)


def seeded_store(task):
    store = ArtifactStore()
    task.setup(store)
    return store


def test_relay_toggle_off_is_single_session_on_is_many_same_path():
    task = MarkerRelayTask()
    off = run_task(seeded_store(task), llm(), task, relay=False, budget=Budget(None))
    on = run_task(seeded_store(task), llm(), task, relay=True, budget=Budget(BUDGET))
    assert off.sessions == 1
    assert on.sessions > 1


def test_peak_and_single_shot_tokens_are_measured():
    matrix = run_experiment_matrix(MarkerRelayTask(), llm(), BUDGET)
    # single_shot from the relay-off unbounded run; peak from the relay-on run
    assert matrix.single_shot_tokens > BUDGET
    assert matrix.relay_on_bounded.peak_session_tokens <= BUDGET


def test_three_cell_matrix_falsification_result():
    matrix = run_experiment_matrix(MarkerRelayTask(), llm(), BUDGET)
    assert matrix.relay_off_unbounded.acceptance == "complete"
    assert matrix.relay_off_bounded.acceptance == "not-complete"
    assert matrix.relay_on_bounded.acceptance == "complete"
    assert (
        matrix.relay_on_bounded.peak_session_tokens
        <= matrix.budget
        < matrix.single_shot_tokens
    )
    assert matrix.bet_holds is True


def test_acceptance_verdict_is_complete_or_not_complete():
    matrix = run_experiment_matrix(MarkerRelayTask(), llm(), BUDGET)
    for cell in (
        matrix.relay_off_unbounded,
        matrix.relay_off_bounded,
        matrix.relay_on_bounded,
    ):
        assert cell.acceptance in {"complete", "not-complete"}
