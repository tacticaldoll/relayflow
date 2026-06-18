from relayflow.artifact import Artifact, ArtifactStore
from relayflow.firewall import (
    PIPELINE_STAGES,
    AssembledContext,
    Budget,
    ContextPolicy,
    assemble,
    distill_scope,
)
from relayflow.llm import MockLLM
from relayflow.tokens import count_tokens


def seed(store, scope="task"):
    store.put(Artifact(scope, "a", "note", "alpha one", {"tags": ["keep"]}))
    store.put(Artifact(scope, "b", "note", "bravo two", {"tags": ["drop"]}))
    store.put(Artifact(scope, "c", "note", "charlie three", {"tags": ["keep"]}))


def test_pipeline_runs_all_four_stages_in_order_and_within_budget():
    store = ArtifactStore()
    seed(store)
    ctx = assemble(store, "task", ContextPolicy("latest"), Budget(max_tokens=4))
    assert isinstance(ctx, AssembledContext)
    assert ctx.stages == list(PIPELINE_STAGES)
    assert ctx.tokens <= 4


def test_latest_policy_selects_recent_first():
    store = ArtifactStore()
    seed(store)
    ctx = assemble(store, "task", ContextPolicy("latest", limit=2), Budget())
    assert ctx.included_refs == ["artifact://task/c", "artifact://task/b"]


def test_tagged_policy_selects_by_tag():
    store = ArtifactStore()
    seed(store)
    ctx = assemble(store, "task", ContextPolicy("tagged", tag="keep"), Budget())
    assert set(ctx.included_refs) == {"artifact://task/a", "artifact://task/c"}


def test_oversized_context_is_truncated_to_budget():
    store = ArtifactStore()
    store.put(Artifact("task", "big", "note", " ".join(map(str, range(50))), {}))
    ctx = assemble(store, "task", ContextPolicy("latest"), Budget(max_tokens=5))
    assert ctx.truncated is True
    assert ctx.tokens <= 5


def test_within_budget_context_not_truncated():
    store = ArtifactStore()
    store.put(Artifact("task", "small", "note", "one two", {}))
    ctx = assemble(store, "task", ContextPolicy("latest"), Budget(max_tokens=10))
    assert ctx.truncated is False
    assert ctx.text == "one two"


def test_compression_applied_for_oversized_artifacts():
    store = ArtifactStore()
    store.put(Artifact("task", "big", "note", " ".join(map(str, range(100))), {}))
    ctx = assemble(
        store,
        "task",
        ContextPolicy("latest"),
        Budget(max_tokens=1000),
        compression_threshold=10,
        summary_tokens=5,
    )
    # compressed to <= 5 tokens, well under the (large) budget, no truncation
    assert ctx.tokens <= 5
    assert ctx.truncated is False


def test_distill_scope_produces_referenceable_scope_artifact():
    store = ArtifactStore()
    llm = MockLLM(responder=lambda p: "OBJECTIVE: build X\nBOUNDARIES: only Y")
    art = distill_scope(store, "task", "make the thing work", llm)
    assert art.type == "scope"
    assert art.ref == "artifact://task/scope"
    assert store.resolve("artifact://task/scope").content == art.content
    assert count_tokens(art.content) > 0
