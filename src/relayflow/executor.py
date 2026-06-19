"""Executor: drive a real worker (OpenCode) that returns a patch and tests.

The relay so far produced text artifacts from a model. An Executor produces a
**patch** and **test** artifact from a coding worker. It is synchronous and
behind a mockable interface (mirroring ``LLMClient``) so the suite runs without
``opencode`` and without the worklane substrate.

A file-scope guard rejects any patch that touches files outside the declared
``allowed_paths`` and writes nothing — failing loud, leaving the repo unpolluted.
This is a reporting-based guard over what the executor says it touched, not a
sandbox; true isolation is a later (worklane/worktree) concern.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from relayflow.artifact import Artifact, ArtifactStore


class FileScopeViolation(Exception):
    """Raised when a produced patch touches a file outside ``allowed_paths``."""


@dataclass
class ExecSpec:
    id: str
    scope: str
    instruction: str
    allowed_paths: list[str] = field(default_factory=list)


@dataclass
class ExecResult:
    patch: str
    summary: str
    tests: str
    status: str  # "passed" | "failed"
    files: list[str] = field(default_factory=list)


@runtime_checkable
class Executor(Protocol):
    def run(self, spec: ExecSpec) -> ExecResult: ...


@dataclass
class MockExecutor:
    """Deterministic executor for tests and the demo."""

    result: ExecResult

    def run(self, spec: ExecSpec) -> ExecResult:
        return self.result


class OpenCodeExecutor:
    """Real executor that shells ``opencode run`` (integration-only).

    Not exercised by the unit suite; the contract everything depends on is
    ``ExecResult``, which this populates by parsing the worker's output.
    """

    def __init__(self, binary: str = "opencode") -> None:
        self._binary = binary

    def run(self, spec: ExecSpec) -> ExecResult:  # pragma: no cover
        completed = subprocess.run(
            [self._binary, "run", spec.instruction],
            capture_output=True,
            text=True,
            check=False,
        )
        patch = completed.stdout
        files = _files_from_diff(patch)
        status = "passed" if completed.returncode == 0 else "failed"
        return ExecResult(
            patch=patch,
            summary=spec.instruction,
            tests=completed.stderr,
            status=status,
            files=files,
        )


def _files_from_diff(diff: str) -> list[str]:  # pragma: no cover
    files: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            path = line[len("+++ b/") :].strip()
            if path and path not in files:
                files.append(path)
    return files


def _normalize(path: str) -> str:
    return path.strip("/")


def in_scope(touched: str, allowed_paths: list[str]) -> bool:
    """True when ``touched`` equals or sits under one of ``allowed_paths``."""
    t = _normalize(touched)
    for allowed in allowed_paths:
        a = _normalize(allowed)
        if t == a or t.startswith(a + "/"):
            return True
    return False


def run_execution(
    store: ArtifactStore,
    executor: Executor,
    spec: ExecSpec,
) -> tuple[str, str]:
    """Run the executor, enforce file scope, and write patch + test artifacts.

    Returns ``(patch_ref, test_ref)``. Raises ``FileScopeViolation`` (writing
    nothing) if the patch touches a file outside ``spec.allowed_paths``.
    """
    result = executor.run(spec)

    out_of_scope = [f for f in result.files if not in_scope(f, spec.allowed_paths)]
    if out_of_scope:
        raise FileScopeViolation(
            f"patch touches paths outside scope {spec.allowed_paths}: {out_of_scope}"
        )

    patch = Artifact(
        scope=spec.scope,
        id=f"{spec.id}.patch",
        type="patch",
        content=result.patch,
        metadata={"summary": result.summary, "files": result.files, "tags": ["patch"]},
    )
    test = Artifact(
        scope=spec.scope,
        id=f"{spec.id}.test",
        type="test",
        content=result.tests,
        metadata={"status": result.status, "tags": ["test"]},
    )
    store.put(patch)
    store.put(test)
    return patch.ref, test.ref
