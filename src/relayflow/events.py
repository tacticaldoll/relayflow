"""Event bridge: emit lifecycle events and let listeners (Triggerlane) react.

Decouples RelayFlow from the execution/reporting layer behind a mockable bus.
``emit`` is outbound (RelayFlow -> world); ``receive`` is inbound (world ->
RelayFlow, e.g. a Triggerlane report). Both dispatch to the same subscribers.

Synchronous and in-memory by design; real Triggerlane transport and async
park/resume are a worklane concern.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# Event types emitted by a graph run.
NODE_DONE = "node_done"
NODE_FAILED = "node_failed"
NODE_BLOCKED = "node_blocked"
APPROVAL_REQUIRED = "approval_required"
APPROVAL_GRANTED = "approval_granted"
APPROVAL_DENIED = "approval_denied"


@dataclass
class Event:
    type: str
    payload: dict = field(default_factory=dict)


Listener = Callable[[Event], None]


@runtime_checkable
class EventBus(Protocol):
    def emit(self, event: Event) -> None: ...

    def subscribe(self, listener: Listener) -> None: ...


@dataclass
class InMemoryBus:
    """Records emitted events and fans out to subscribers."""

    events: list[Event] = field(default_factory=list)
    listeners: list[Listener] = field(default_factory=list)

    def subscribe(self, listener: Listener) -> None:
        self.listeners.append(listener)

    def emit(self, event: Event) -> None:
        self.events.append(event)
        self._dispatch(event)

    def receive(self, event: Event) -> None:
        """Inbound external event (e.g. a Triggerlane report)."""
        self._dispatch(event)

    def _dispatch(self, event: Event) -> None:
        for listener in self.listeners:
            listener(event)

    def types(self) -> list[str]:
        return [e.type for e in self.events]


class TriggerlaneBus:  # pragma: no cover
    """Stub real bus that would bridge to Triggerlane (integration-only)."""

    def __init__(self) -> None:
        self.listeners: list[Listener] = []

    def subscribe(self, listener: Listener) -> None:
        self.listeners.append(listener)

    def emit(self, event: Event) -> None:
        raise NotImplementedError("real Triggerlane transport not implemented in V1")
