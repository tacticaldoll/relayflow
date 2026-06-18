import json

import pytest

from relayflow.artifact import Artifact, ArtifactStore
from relayflow.firewall import Budget, ContextPolicy
from relayflow.llm import MockLLM
from relayflow.session import (
    SessionContext,
    SessionInput,
    SessionNotFound,
    SessionStore,
    SessionValidationError,
    run_session,
)


def test_session_without_budget_is_rejected():
    with pytest.raises(SessionValidationError):
        SessionInput(id="s1", purpose="p", context=SessionContext(scope="task"))


def test_unbounded_budget_is_a_valid_session():
    si = SessionInput(
        id="s1",
        purpose="p",
        context=SessionContext(scope="task"),
        budget=Budget(max_tokens=None),
    )
    assert si.budget.max_tokens is None


def test_session_output_contract_uses_references():
    store = ArtifactStore()
    llm = MockLLM(responder=lambda p: "result body here")
    si = SessionInput(
        id="s1",
        purpose="do work",
        context=SessionContext(scope="task"),
        budget=Budget(max_tokens=100),
    )
    result = run_session(store, llm, si)
    assert result.output.summary
    assert result.output.artifacts == ["artifact://task/s1.out"]
    assert result.output.next_actions == []
    # the referenced artifact exists in the store
    assert store.resolve("artifact://task/s1.out").content == "result body here"


def test_persistence_keeps_input_output_artifacts_not_reasoning():
    artifacts = ArtifactStore()
    sessions = SessionStore()
    llm = MockLLM(responder=lambda p: "answer")
    si = SessionInput(
        id="s1",
        purpose="do work",
        context=SessionContext(scope="task"),
        constraints=["be brief"],
        budget=Budget(max_tokens=100),
    )
    run_session(artifacts, llm, si, sessions)

    record = sessions.get("s1")
    assert record.input["purpose"] == "do work"
    assert record.output["artifacts"] == ["artifact://task/s1.out"]
    assert record.artifacts == ["artifact://task/s1.out"]

    # the persisted record carries no reasoning trace
    blob = json.dumps({"input": record.input, "output": record.output})
    assert "reasoning" not in blob.lower()


def test_session_consumes_prior_artifact_via_latest_policy():
    store = ArtifactStore()
    store.put(Artifact("task", "seed", "note", "PRIOR-CONTEXT", {}))
    seen = {}

    def responder(prompt):
        seen["prompt"] = prompt
        return "second"

    si = SessionInput(
        id="s2",
        purpose="continue",
        context=SessionContext(scope="task", policy=ContextPolicy("latest")),
        budget=Budget(max_tokens=100),
    )
    run_session(store, MockLLM(responder=responder), si)
    assert "PRIOR-CONTEXT" in seen["prompt"]


def test_get_unknown_session_raises():
    sessions = SessionStore()
    with pytest.raises(SessionNotFound):
        sessions.get("nope")
