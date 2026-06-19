"""The V0 demo task: marker assembly.

A source split across several verbose groups, each carrying a few distinct
markers. The whole-task answer needs *every* marker. Holding the entire source
at once needs far more than the budget, so a single bounded session loses
markers to truncation. The relay extracts each group's markers into a tiny
artifact, then synthesizes the compact extracts — each session staying within
budget while the work still completes.

The ``marker_responder`` is a deterministic stand-in for an LLM: it echoes the
distinct markers it can see in its prompt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from relayflow.artifact import Artifact, ArtifactStore
from relayflow.executor import ExecResult, ExecSpec, MockExecutor
from relayflow.firewall import Budget, ContextPolicy
from relayflow.graph import SessionGraph
from relayflow.session import SessionContext, SessionInput, SessionResult

MARKER_RE = re.compile(r"^m\d{3}$")


def marker(i: int) -> str:
    return f"m{i:03d}"


def extract_markers(text: str) -> list[str]:
    """Distinct markers visible in ``text``, in first-seen order."""
    seen: list[str] = []
    for token in text.split():
        if MARKER_RE.match(token) and token not in seen:
            seen.append(token)
    return seen


def marker_responder(prompt: str) -> str:
    """Deterministic LLM: echo the distinct markers found in the prompt."""
    return " ".join(extract_markers(prompt))


@dataclass
class MarkerRelayTask:
    scope: str = "demo"
    num_groups: int = 4
    facts_per_group: int = 3
    padding_tokens: int = 40

    @property
    def total_facts(self) -> int:
        return self.num_groups * self.facts_per_group

    def _all_markers(self) -> list[str]:
        return [marker(i) for i in range(self.total_facts)]

    def _group_ref(self, group: int) -> str:
        return f"artifact://{self.scope}/group{group}"

    def setup(self, artifacts: ArtifactStore) -> None:
        markers = self._all_markers()
        padding = " ".join(["lorem"] * self.padding_tokens)
        for group in range(self.num_groups):
            start = group * self.facts_per_group
            facts = markers[start : start + self.facts_per_group]
            content = " ".join(facts) + " " + padding
            artifacts.put(
                Artifact(
                    scope=self.scope,
                    id=f"group{group}",
                    type="source",
                    content=content,
                    metadata={"tags": ["source"]},
                )
            )

    def single_shot(self, budget: Budget) -> list[SessionInput]:
        refs = [self._group_ref(g) for g in range(self.num_groups)]
        return [
            SessionInput(
                id="single",
                purpose="extract all markers",
                context=SessionContext(scope=self.scope, inputs=refs),
                budget=budget,
            )
        ]

    def relay_steps(self, budget: Budget) -> list[SessionInput]:
        steps = [
            SessionInput(
                id=f"extract{g}",
                purpose="extract markers from this group",
                context=SessionContext(scope=self.scope, inputs=[self._group_ref(g)]),
                budget=budget,
            )
            for g in range(self.num_groups)
        ]
        steps.append(
            SessionInput(
                id="synthesis",
                purpose="combine extracted markers",
                context=SessionContext(
                    scope=self.scope,
                    policy=ContextPolicy(kind="tagged", tag="result"),
                ),
                budget=budget,
            )
        )
        return steps

    def is_complete(self, artifacts: ArtifactStore, result: SessionResult) -> bool:
        final = artifacts.resolve(result.output.artifacts[-1]).content
        return set(self._all_markers()) <= set(extract_markers(final))

    def graph_steps(self, budget: Budget) -> list[SessionInput]:
        """Like ``relay_steps`` but the sink depends on explicit extract refs.

        Explicit input references let the Session Graph derive edges (extract
        nodes -> synthesis) rather than relying on a tagged-policy sweep.
        """
        extracts = [
            SessionInput(
                id=f"extract{g}",
                purpose="extract markers from this group",
                context=SessionContext(scope=self.scope, inputs=[self._group_ref(g)]),
                budget=budget,
            )
            for g in range(self.num_groups)
        ]
        synthesis = SessionInput(
            id="synthesis",
            purpose="combine extracted markers",
            context=SessionContext(
                scope=self.scope,
                inputs=[
                    f"artifact://{self.scope}/extract{g}.out"
                    for g in range(self.num_groups)
                ],
            ),
            budget=budget,
        )
        return [*extracts, synthesis]


def build_marker_graph(task: MarkerRelayTask, budget: Budget) -> SessionGraph:
    """Build a Session Graph for the marker task: extract nodes -> synthesis."""
    graph = SessionGraph()
    for step in task.graph_steps(budget):
        graph.add_node(step)
    return graph


def build_mixed_graph() -> SessionGraph:
    """A heterogeneous graph: a session 'plan' feeds an execution 'impl'.

    Demonstrates session and execution nodes coexisting, with the execution
    depending on the session's artifact and gated on its tests.
    """
    graph = SessionGraph()
    graph.add_node(
        SessionInput(
            id="plan",
            purpose="plan the change",
            context=SessionContext(scope="mixed"),
            budget=Budget(max_tokens=100),
        )
    )
    executor, _ = demo_execution()
    spec = ExecSpec(
        id="impl",
        scope="mixed",
        instruction="implement the plan under src/",
        allowed_paths=["src/"],
    )
    graph.add_execution(spec, executor, deps=["artifact://mixed/plan.out"])
    return graph


def demo_execution() -> tuple[MockExecutor, ExecSpec]:
    """A deterministic in-scope execution: add a function under ``src/``."""
    spec = ExecSpec(
        id="addgreet",
        scope="exec",
        instruction="add a greet() function to src/greeter.py",
        allowed_paths=["src/"],
    )
    result = ExecResult(
        patch=(
            "--- a/src/greeter.py\n"
            "+++ b/src/greeter.py\n"
            "+def greet():\n"
            "+    return 'hello'\n"
        ),
        summary="add greet() to src/greeter.py",
        tests="test_greet ... ok",
        status="passed",
        files=["src/greeter.py"],
    )
    return MockExecutor(result=result), spec
