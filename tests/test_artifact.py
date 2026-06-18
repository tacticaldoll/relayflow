import pytest

from relayflow.artifact import (
    Artifact,
    ArtifactNotFound,
    ArtifactStore,
    compress,
    parse_reference,
    resolve_all,
    should_compress,
)
from relayflow.tokens import count_tokens


def make(scope="task", id="a", content="hello world", **md):
    return Artifact(scope=scope, id=id, type="note", content=content, metadata=md)


def test_artifact_has_type_content_metadata_and_ref():
    art = make(content="body", tags=["x"])
    assert art.type == "note"
    assert art.content == "body"
    assert art.metadata["tags"] == ["x"]
    assert art.ref == "artifact://task/a"


def test_store_round_trip():
    store = ArtifactStore()
    ref = store.put(make(content="payload", tags=["k"]))
    got = store.resolve(ref)
    assert got.type == "note"
    assert got.content == "payload"
    assert got.metadata["tags"] == ["k"]


def test_reading_missing_artifact_signals_not_found():
    store = ArtifactStore()
    with pytest.raises(ArtifactNotFound):
        store.get("task", "does-not-exist")


def test_parse_reference_valid_and_invalid():
    assert parse_reference("artifact://scope/123") == ("scope", "123")
    for bad in ["scope/123", "artifact://scope", "artifact://", "artifact:///id"]:
        with pytest.raises(ValueError):
            parse_reference(bad)


def test_resolve_all_fails_fast_on_missing_reference():
    store = ArtifactStore()
    store.put(make(id="present"))
    with pytest.raises(ArtifactNotFound):
        resolve_all(store, ["artifact://task/present", "artifact://task/missing"])


def test_latest_orders_most_recent_first():
    store = ArtifactStore()
    store.put(make(id="first"))
    store.put(make(id="second"))
    ids = [a.id for a in store.latest("task")]
    assert ids == ["second", "first"]


def test_tagged_selects_by_metadata_tag():
    store = ArtifactStore()
    store.put(make(id="t1", tags=["keep"]))
    store.put(make(id="t2", tags=["other"]))
    assert [a.id for a in store.tagged("task", "keep")] == ["t1"]


def test_compression_shrinks_tokens_and_preserves_original():
    store = ArtifactStore()
    big = make(id="big", content=" ".join(str(n) for n in range(100)))
    store.put(big)
    assert should_compress(big, threshold_tokens=20)

    summary = compress(big, target_tokens=10)
    assert count_tokens(summary.content) <= 10
    assert count_tokens(summary.content) < count_tokens(big.content)
    assert summary.metadata["compressed_from"] == big.ref

    # original stays retrievable, unchanged
    assert store.resolve(big.ref).content == big.content
