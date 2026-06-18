"""Artifact System: typed session outputs, SQLite store, references, compression.

Artifacts are the only thing sessions pass to one another, and they are passed
**by reference** (``artifact://scope/id``), never inlined. This module owns the
artifact type, its persistence, reference parsing/resolution, and compression.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field

from relayflow.tokens import count_tokens, truncate_to_tokens

ARTIFACT_SCHEME = "artifact://"


class ArtifactNotFound(KeyError):
    """Raised when a scope/id (or reference) is not present in the store."""


@dataclass(frozen=True)
class Artifact:
    """A structured session output addressable by ``scope`` + ``id``."""

    scope: str
    id: str
    type: str
    content: str
    metadata: dict = field(default_factory=dict)

    @property
    def ref(self) -> str:
        return f"{ARTIFACT_SCHEME}{self.scope}/{self.id}"

    @property
    def tags(self) -> list[str]:
        tags = self.metadata.get("tags", [])
        return list(tags)


def parse_reference(ref: str) -> tuple[str, str]:
    """Parse ``artifact://scope/id`` into ``(scope, id)``.

    Raises ``ValueError`` for anything that is not a well-formed reference.
    """
    if not ref.startswith(ARTIFACT_SCHEME):
        raise ValueError(f"not an artifact reference: {ref!r}")
    rest = ref[len(ARTIFACT_SCHEME) :]
    scope, sep, artifact_id = rest.partition("/")
    if not sep or not scope or not artifact_id:
        raise ValueError(f"malformed artifact reference: {ref!r}")
    return scope, artifact_id


class ArtifactStore:
    """SQLite-backed artifact store.

    Insertion order is preserved via an autoincrementing ``seq`` so the
    Context Firewall's ``latest`` policy has a stable recency order.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                seq      INTEGER PRIMARY KEY AUTOINCREMENT,
                scope    TEXT NOT NULL,
                id       TEXT NOT NULL,
                type     TEXT NOT NULL,
                content  TEXT NOT NULL,
                metadata TEXT NOT NULL,
                UNIQUE (scope, id) ON CONFLICT REPLACE
            )
            """
        )
        self._conn.commit()

    def put(self, artifact: Artifact) -> str:
        """Persist ``artifact`` and return its reference."""
        self._conn.execute(
            "INSERT INTO artifacts (scope, id, type, content, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                artifact.scope,
                artifact.id,
                artifact.type,
                artifact.content,
                json.dumps(artifact.metadata),
            ),
        )
        self._conn.commit()
        return artifact.ref

    def get(self, scope: str, artifact_id: str) -> Artifact:
        row = self._conn.execute(
            "SELECT scope, id, type, content, metadata FROM artifacts "
            "WHERE scope = ? AND id = ?",
            (scope, artifact_id),
        ).fetchone()
        if row is None:
            raise ArtifactNotFound(f"{ARTIFACT_SCHEME}{scope}/{artifact_id}")
        return self._row_to_artifact(row)

    def resolve(self, ref: str) -> Artifact:
        """Resolve an ``artifact://scope/id`` reference to an Artifact."""
        scope, artifact_id = parse_reference(ref)
        return self.get(scope, artifact_id)

    def latest(self, scope: str, limit: int | None = None) -> list[Artifact]:
        """Return artifacts in ``scope`` most-recent first."""
        sql = (
            "SELECT scope, id, type, content, metadata FROM artifacts "
            "WHERE scope = ? ORDER BY seq DESC"
        )
        params: tuple = (scope,)
        if limit is not None:
            sql += " LIMIT ?"
            params = (scope, limit)
        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_artifact(row) for row in rows]

    def tagged(self, scope: str, tag: str) -> list[Artifact]:
        """Return artifacts in ``scope`` whose metadata carries ``tag``."""
        return [a for a in self.latest(scope) if tag in a.tags]

    @staticmethod
    def _row_to_artifact(row: sqlite3.Row) -> Artifact:
        return Artifact(
            scope=row["scope"],
            id=row["id"],
            type=row["type"],
            content=row["content"],
            metadata=json.loads(row["metadata"]),
        )


def naive_summarize(text: str, target_tokens: int) -> str:
    """Deterministic V0 summarizer: keep the leading ``target_tokens`` tokens."""
    return truncate_to_tokens(text, target_tokens)


def compress(
    artifact: Artifact,
    target_tokens: int,
    summarizer=naive_summarize,
) -> Artifact:
    """Return a smaller summary artifact derived from ``artifact``.

    The summary records the source reference in its metadata; the original
    artifact is never mutated, so it stays retrievable from the store.
    """
    summary = summarizer(artifact.content, target_tokens)
    metadata = dict(artifact.metadata)
    metadata["compressed_from"] = artifact.ref
    metadata["original_tokens"] = count_tokens(artifact.content)
    return Artifact(
        scope=artifact.scope,
        id=f"{artifact.id}#summary",
        type="summary",
        content=summary,
        metadata=metadata,
    )


def should_compress(artifact: Artifact, threshold_tokens: int) -> bool:
    """True when ``artifact`` content exceeds the configured token threshold."""
    return count_tokens(artifact.content) > threshold_tokens


def resolve_all(store: ArtifactStore, refs: Sequence[str]) -> list[Artifact]:
    """Resolve a sequence of references, failing fast on the first missing one."""
    return [store.resolve(ref) for ref in refs]
