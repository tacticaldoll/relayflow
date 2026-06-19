import pytest

from relayflow.artifact import Artifact, ArtifactStore
from relayflow.firewall import (
    Budget,
    ContextPolicy,
    assemble,
    relevance_score,
)


def put(store, id, content, scope="task"):
    store.put(Artifact(scope, id, "note", content, {}))


def test_relevance_score_counts_distinct_query_terms():
    assert relevance_score("alpha beta alpha", {"alpha", "gamma"}) == 1
    assert relevance_score("alpha beta", {"alpha", "beta"}) == 2
    assert relevance_score("nothing here", {"alpha"}) == 0


def test_higher_overlap_ranks_first():
    store = ArtifactStore()
    put(store, "a", "alpha")
    put(store, "b", "alpha beta gamma")
    sel = ContextPolicy("relevant", query="alpha beta gamma").select(store, "task")
    assert [a.id for a in sel] == ["b", "a"]


def test_ties_break_by_recency():
    store = ArtifactStore()
    put(store, "old", "alpha")
    put(store, "new", "alpha")  # same overlap, produced later
    sel = ContextPolicy("relevant", query="alpha").select(store, "task")
    assert [a.id for a in sel] == ["new", "old"]


def test_limit_caps_selection():
    store = ArtifactStore()
    for i in range(5):
        put(store, f"a{i}", "alpha")
    sel = ContextPolicy("relevant", query="alpha", limit=2).select(store, "task")
    assert len(sel) == 2


def test_no_overlap_selects_nothing():
    store = ArtifactStore()
    put(store, "a", "beta gamma")
    sel = ContextPolicy("relevant", query="alpha").select(store, "task")
    assert sel == []


def test_relevant_without_query_raises():
    store = ArtifactStore()
    with pytest.raises(ValueError):
        ContextPolicy("relevant").select(store, "task")


def test_assemble_pipeline_with_relevant_policy():
    store = ArtifactStore()
    put(store, "hit", "alpha beta")
    put(store, "miss", "zeta")
    ctx = assemble(
        store,
        "task",
        ContextPolicy("relevant", query="alpha"),
        Budget(max_tokens=100),
    )
    assert ctx.included_refs == ["artifact://task/hit"]
    assert ctx.stages == ["selection", "reference", "compression", "budget"]
