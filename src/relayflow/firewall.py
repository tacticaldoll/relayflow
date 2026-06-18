"""Context Firewall: the single entry point for context entering a session.

Every session's context is produced by one fixed pipeline applied in order:

    Selection -> Reference -> Compression -> Budget

Nothing may bypass it. ``latest`` and ``tagged`` selection policies are
supported in V0; ``relevant`` is deliberately out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from relayflow.artifact import Artifact, ArtifactStore, compress, should_compress
from relayflow.llm import LLMClient
from relayflow.tokens import count_tokens, truncate_to_tokens

PIPELINE_STAGES = ("selection", "reference", "compression", "budget")


@dataclass(frozen=True)
class Budget:
    """A token ceiling. ``max_tokens=None`` means unbounded (relay-off)."""

    max_tokens: int | None = None


@dataclass(frozen=True)
class ContextPolicy:
    """Selection policy. ``kind`` is ``"latest"`` or ``"tagged"``."""

    kind: str = "latest"
    limit: int | None = None
    tag: str | None = None

    def select(self, store: ArtifactStore, scope: str) -> list[Artifact]:
        if self.kind == "latest":
            return store.latest(scope, self.limit)
        if self.kind == "tagged":
            if self.tag is None:
                raise ValueError("tagged policy requires a tag")
            return store.tagged(scope, self.tag)
        raise ValueError(f"unknown context policy: {self.kind!r}")


@dataclass
class AssembledContext:
    text: str
    tokens: int
    included_refs: list[str] = field(default_factory=list)
    stages: list[str] = field(default_factory=list)
    truncated: bool = False


def assemble(
    store: ArtifactStore,
    scope: str,
    policy: ContextPolicy,
    budget: Budget,
    *,
    preamble: str = "",
    compression_threshold: int | None = None,
    summary_tokens: int | None = None,
) -> AssembledContext:
    """Run the four-stage pipeline and return the assembled context."""
    stages: list[str] = []

    # 1. Selection — choose which artifacts enter.
    selected = policy.select(store, scope)
    stages.append("selection")

    # 2. Reference — artifacts are carried by reference, resolved here.
    included_refs = [a.ref for a in selected]
    stages.append("reference")

    # 3. Compression — shrink any chosen artifact over the threshold.
    if compression_threshold is not None:
        target = summary_tokens if summary_tokens is not None else compression_threshold
        selected = [
            compress(a, target) if should_compress(a, compression_threshold) else a
            for a in selected
        ]
    stages.append("compression")

    # 4. Budget — enforce the hard token ceiling via truncation.
    parts = [preamble] if preamble else []
    parts.extend(a.content for a in selected)
    text = "\n\n".join(parts)
    truncated = False
    if budget.max_tokens is not None and count_tokens(text) > budget.max_tokens:
        text = truncate_to_tokens(text, budget.max_tokens)
        truncated = True
    stages.append("budget")

    return AssembledContext(
        text=text,
        tokens=count_tokens(text),
        included_refs=included_refs,
        stages=stages,
        truncated=truncated,
    )


def distill_scope(
    store: ArtifactStore,
    scope: str,
    request: str,
    llm: LLMClient,
    *,
    artifact_id: str = "scope",
) -> Artifact:
    """Turn a vague request into an explicit, referenceable scope artifact."""
    explicit = llm.complete(
        "Distill the following request into an explicit scope with objective "
        f"and boundaries:\n{request}"
    )
    artifact = Artifact(
        scope=scope,
        id=artifact_id,
        type="scope",
        content=explicit,
        metadata={"tags": ["scope"]},
    )
    store.put(artifact)
    return artifact
