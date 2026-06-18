"""Session Runtime: bounded units of LLM work, their output, persistence, inspect.

A Session has a token-bounded context, produces a structured output
(summary / artifacts / next_actions), and is persisted as input/output/artifact
references only — never the model's full reasoning.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field

from relayflow.artifact import Artifact, ArtifactStore
from relayflow.firewall import Budget, ContextPolicy, assemble
from relayflow.llm import LLMClient
from relayflow.tokens import truncate_to_tokens

SUMMARY_TOKENS = 30


class SessionValidationError(ValueError):
    """Raised when a session is missing required fields."""


class SessionNotFound(KeyError):
    """Raised when a session id is not present in the session store."""


@dataclass
class SessionContext:
    """Where a session draws its context from."""

    scope: str
    policy: ContextPolicy = field(default_factory=ContextPolicy)
    inputs: list[str] = field(default_factory=list)
    preamble: str = ""
    compression_threshold: int | None = None
    summary_tokens: int | None = None


@dataclass
class SessionInput:
    id: str
    purpose: str
    context: SessionContext
    constraints: list[str] = field(default_factory=list)
    budget: Budget | None = None

    def __post_init__(self) -> None:
        # A session must carry a budget. Relay-off uses an explicit unbounded
        # budget (Budget(max_tokens=None)); a missing budget is rejected.
        if self.budget is None:
            raise SessionValidationError(f"session {self.id!r} has no budget")


@dataclass
class SessionOutput:
    summary: str
    artifacts: list[str]
    next_actions: list[str] = field(default_factory=list)


@dataclass
class SessionResult:
    session_id: str
    output: SessionOutput
    context_tokens: int


@dataclass
class SessionRecord:
    id: str
    input: dict
    output: dict
    artifacts: list[str]


def _preamble(si: SessionInput) -> str:
    lines = [f"PURPOSE: {si.purpose}"]
    if si.context.preamble:
        lines.append(si.context.preamble)
    if si.constraints:
        lines.append("CONSTRAINTS:")
        lines.extend(f"- {c}" for c in si.constraints)
    return "\n".join(lines)


class SessionStore:
    """SQLite persistence of input/output/artifacts. No reasoning is stored."""

    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id        TEXT PRIMARY KEY,
                input     TEXT NOT NULL,
                output    TEXT NOT NULL,
                artifacts TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def save(self, record: SessionRecord) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO sessions (id, input, output, artifacts) "
            "VALUES (?, ?, ?, ?)",
            (
                record.id,
                json.dumps(record.input),
                json.dumps(record.output),
                json.dumps(record.artifacts),
            ),
        )
        self._conn.commit()

    def get(self, session_id: str) -> SessionRecord:
        row = self._conn.execute(
            "SELECT id, input, output, artifacts FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            raise SessionNotFound(session_id)
        return SessionRecord(
            id=row["id"],
            input=json.loads(row["input"]),
            output=json.loads(row["output"]),
            artifacts=json.loads(row["artifacts"]),
        )


def run_session(
    artifacts: ArtifactStore,
    llm: LLMClient,
    si: SessionInput,
    sessions: SessionStore | None = None,
) -> SessionResult:
    """Assemble context via the firewall, call the model, persist, emit output."""
    ctx = assemble(
        artifacts,
        si.context.scope,
        si.context.policy,
        si.budget,
        explicit_refs=si.context.inputs or None,
        preamble=_preamble(si),
        compression_threshold=si.context.compression_threshold,
        summary_tokens=si.context.summary_tokens,
    )

    completion = llm.complete(ctx.text)

    out_artifact = Artifact(
        scope=si.context.scope,
        id=f"{si.id}.out",
        type="result",
        content=completion,
        metadata={"tags": ["result"], "session": si.id},
    )
    artifacts.put(out_artifact)

    output = SessionOutput(
        summary=truncate_to_tokens(completion, SUMMARY_TOKENS),
        artifacts=[out_artifact.ref],
        next_actions=[],
    )

    if sessions is not None:
        sessions.save(
            SessionRecord(
                id=si.id,
                input=asdict(si),
                output=asdict(output),
                artifacts=output.artifacts,
            )
        )

    return SessionResult(session_id=si.id, output=output, context_tokens=ctx.tokens)
