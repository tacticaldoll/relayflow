## Context

RelayFlow needs to drive a real worker (OpenCode) that returns a patch and tests,
not just a text completion. This change adds that behind a mockable interface,
synchronously, reusing the artifact store. It mirrors the `LLMClient` / `MockLLM`
pattern so the suite runs without `opencode` and without the worklane substrate.

## Goals / Non-Goals

**Goals:**
- An `Executor` interface with a real `OpenCodeExecutor` and a `MockExecutor`.
- Patch and test artifacts produced into the store and addressable by reference.
- A file-scope guard that rejects out-of-scope patches and writes nothing.

**Non-Goals:**
- worklane / async / concurrent dispatch / retries-as-jobs.
- Wiring the executor as a Session Graph node type (a follow-up change).
- Triggerlane, autonomous planning, real `opencode` invocation in tests.

## Decisions

- **Executor returns structured `files`, not just a diff.** `ExecResult` carries
  `patch`, `summary`, `tests`, `status`, and `files` (touched paths). The
  scope guard checks `files` directly rather than parsing the diff, keeping the
  check robust; the real executor populates `files` by parsing `opencode` output.
- **Scope guard runs before any write.** `run_execution` validates that every
  touched file is within `allowed_paths`; on violation it raises
  `FileScopeViolation` and writes nothing — failing loud, repo unpolluted.
- **"Within scope" = path-prefix containment.** A touched file is in scope if it
  is equal to, or under, one of the allowed paths (normalized). Simple and
  predictable for V1.
- **Two artifacts per execution, deterministic ids.** `{id}.patch` (type `patch`,
  metadata `summary` + `files`) and `{id}.test` (type `test`, metadata `status`).
- **Real `OpenCodeExecutor` is integration-only.** It shells `opencode run` and
  parses output; it is never exercised by the unit suite (no `opencode` assumed).

## Risks / Trade-offs

- **Diff parsing in the real executor is brittle** → isolate it in
  `OpenCodeExecutor`; the contract (`ExecResult.files`) is what everything else
  depends on, so the mock and graph integration stay parser-independent.
- **Scope guard false sense of safety** → it constrains only what the executor
  reports as touched; a misbehaving real worker could still write files. V1
  documents this as a reporting-based guard, not a sandbox; true isolation is a
  later (worklane/worktree) concern.
- **Over-coupling to OpenCode** → the interface is generic (`Executor`); OpenCode
  is one implementation, so a different worker drops in later.
