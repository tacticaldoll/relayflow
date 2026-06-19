"""Broker abstraction: the durable job substrate the scheduler drives.

The contract mirrors worklane's lifecycle (enqueue / reserve / ack / retry /
dead-letter, with delayed enqueue and unique-key dedup) so that a worklane-backed
broker is a drop-in replacement in a later change. The job payload is a thin
envelope (``{graph_id, node_id}``) — never business truth.

``InMemoryBroker`` is the pure-Python implementation used for the synchronous
path and for tests; no external service is required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class Job:
    payload: dict
    unique_key: str | None = None


@runtime_checkable
class Broker(Protocol):
    def enqueue(
        self, payload: dict, *, unique_key: str | None = None, delay: int = 0
    ) -> None: ...

    def reserve(self) -> Job | None: ...

    def ack(self, job: Job) -> None: ...

    def retry(self, job: Job) -> None: ...

    def dead_letter(self, job: Job) -> None: ...


@dataclass
class InMemoryBroker:
    """FIFO broker with unique-key dedup, retry re-delivery, and a dead-letter list.

    ``delay`` is accepted for contract parity (durable park/timeout) but, in the
    synchronous in-memory broker, a delayed job simply joins the queue.
    """

    _queue: list[Job] = field(default_factory=list)
    _keys: set[str] = field(default_factory=set)
    dead: list[Job] = field(default_factory=list)

    def enqueue(
        self, payload: dict, *, unique_key: str | None = None, delay: int = 0
    ) -> None:
        if unique_key is not None and unique_key in self._keys:
            return
        self._queue.append(Job(payload=payload, unique_key=unique_key))
        if unique_key is not None:
            self._keys.add(unique_key)

    def reserve(self) -> Job | None:
        if not self._queue:
            return None
        job = self._queue.pop(0)
        if job.unique_key is not None:
            self._keys.discard(job.unique_key)
        return job

    def ack(self, job: Job) -> None:
        # Reserved jobs are already removed from the queue; ack is a no-op here.
        return None

    def retry(self, job: Job) -> None:
        self._queue.append(job)
        if job.unique_key is not None:
            self._keys.add(job.unique_key)

    def dead_letter(self, job: Job) -> None:
        self.dead.append(job)

    def pending(self) -> int:
        return len(self._queue)
