"""Relay Falsification: the toggle, token metering, acceptance, and the matrix.

The bet is proved by running the *same code path* in two modes:

* relay **on**  — the task's decomposed bounded sessions.
* relay **off** — a degenerate single session (one node) with an unbounded
  budget, or the same bounded budget.

The three-cell matrix then shows that under a bounded budget the task fails
without relay and completes with it, while ``peak_session_tokens`` stays within
budget and ``single_shot_tokens`` (measured, not estimated) far exceeds it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from relayflow.artifact import ArtifactStore
from relayflow.firewall import Budget
from relayflow.llm import LLMClient
from relayflow.session import SessionInput, SessionResult, SessionStore, run_session


@runtime_checkable
class Task(Protocol):
    """A relayable task: how to seed it, decompose it, run it whole, and judge it."""

    scope: str

    def setup(self, artifacts: ArtifactStore) -> None: ...

    def relay_steps(self, budget: Budget) -> list[SessionInput]: ...

    def single_shot(self, budget: Budget) -> list[SessionInput]: ...

    def is_complete(self, artifacts: ArtifactStore, result: SessionResult) -> bool: ...


@dataclass
class RunReport:
    mode: str  # "relay-on" | "relay-off"
    budget: int | None
    sessions: int
    peak_session_tokens: int
    acceptance: str  # "complete" | "not-complete"


def run_task(
    artifacts: ArtifactStore,
    llm: LLMClient,
    task: Task,
    *,
    relay: bool,
    budget: Budget,
    sessions: SessionStore | None = None,
) -> RunReport:
    """Run a task through the relay loop.

    With ``relay=False`` the task is executed as a single session; with
    ``relay=True`` as its decomposed steps. Both go through the same loop and
    the same ``run_session`` call — relay-off is just N=1.
    """
    steps = task.relay_steps(budget) if relay else task.single_shot(budget)
    peak = 0
    last: SessionResult | None = None
    for step in steps:
        result = run_session(artifacts, llm, step, sessions)
        peak = max(peak, result.context_tokens)
        last = result
    verdict = (
        "complete"
        if last is not None and task.is_complete(artifacts, last)
        else "not-complete"
    )
    return RunReport(
        mode="relay-on" if relay else "relay-off",
        budget=budget.max_tokens,
        sessions=len(steps),
        peak_session_tokens=peak,
        acceptance=verdict,
    )


@dataclass
class MatrixResult:
    budget: int
    single_shot_tokens: int
    relay_off_unbounded: RunReport
    relay_off_bounded: RunReport
    relay_on_bounded: RunReport

    @property
    def bet_holds(self) -> bool:
        """True when the three cells confirm the relay bet."""
        return (
            self.relay_off_bounded.acceptance == "not-complete"
            and self.relay_on_bounded.acceptance == "complete"
            and self.relay_on_bounded.peak_session_tokens
            <= self.budget
            < self.single_shot_tokens
        )


def run_experiment_matrix(
    task: Task,
    llm: LLMClient,
    budget_tokens: int,
) -> MatrixResult:
    """Run the three-cell falsification matrix on a fresh store per cell."""

    def fresh() -> ArtifactStore:
        store = ArtifactStore()
        task.setup(store)
        return store

    bounded = Budget(max_tokens=budget_tokens)
    unbounded = Budget(max_tokens=None)

    cell1 = run_task(fresh(), llm, task, relay=False, budget=unbounded)
    cell2 = run_task(fresh(), llm, task, relay=False, budget=bounded)
    cell3 = run_task(fresh(), llm, task, relay=True, budget=bounded)

    return MatrixResult(
        budget=budget_tokens,
        single_shot_tokens=cell1.peak_session_tokens,
        relay_off_unbounded=cell1,
        relay_off_bounded=cell2,
        relay_on_bounded=cell3,
    )
