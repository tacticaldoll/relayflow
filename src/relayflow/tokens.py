"""Deterministic token accounting for RelayFlow.

V0 uses a simple whitespace tokenizer. The falsification bet depends on the
*relative* relationship ``peak_session_tokens <= budget < single_shot_tokens``,
not on matching any specific model's tokenizer, so a stable, dependency-free
count is sufficient and keeps experiments reproducible.
"""

from __future__ import annotations


def count_tokens(text: str) -> int:
    """Return the token count of ``text`` under the V0 tokenizer."""
    return len(text.split())


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Return ``text`` reduced to at most ``max_tokens`` tokens."""
    if max_tokens < 0:
        raise ValueError("max_tokens must be non-negative")
    words = text.split()
    if len(words) <= max_tokens:
        return text
    return " ".join(words[:max_tokens])
