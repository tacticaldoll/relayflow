"""LLM client interface and a deterministic mock.

The runtime talks to models only through ``LLMClient`` so the relay mechanics,
the firewall, and the falsification matrix can all be driven by a deterministic
``MockLLM`` in tests — the bet must be reproducible without a live model.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    def complete(self, prompt: str) -> str: ...


@dataclass
class MockLLM:
    """Deterministic client. ``responder`` maps a prompt to a completion."""

    responder: Callable[[str], str] | None = None
    calls: list[str] = field(default_factory=list)

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if self.responder is None:
            return prompt
        return self.responder(prompt)
