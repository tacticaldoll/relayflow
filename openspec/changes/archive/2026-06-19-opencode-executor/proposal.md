## Why

V0 and the Session Graph proved relay mechanics with a deterministic in-process
model. The next V1 question is: **can the relay drive a real worker?** OpenCode
is the first such worker — it runs a coding task and returns a patch plus tests.

This change adds an executor abstraction and the artifacts a worker produces,
**synchronously and behind a mockable interface** (mirroring `LLMClient`), so the
capability is testable without `opencode` installed and without committing to the
worklane execution substrate or the Rust/Python boundary. Async dispatch,
concurrency, and retries-as-jobs remain a later worklane change.

## What Changes

- Add an **Executor** interface (`run(spec) -> result`) with a real
  `OpenCodeExecutor` (shells `opencode run`) and a deterministic `MockExecutor`.
- Add a **Patch Artifact**: an executor produces a `patch` (diff) plus a
  `summary`, stored as a referenceable artifact.
- Add a **Test Artifact**: an executor produces `tests` plus a `status`
  (`passed`/`failed`), stored as a referenceable artifact.
- Add a **File Scope** guard: an execution declares `allowed_paths`; if the
  produced patch touches any path outside scope, the execution is rejected and
  **no artifacts are written** (avoid polluting the repo).
- Extend the CLI with an `execute` command that runs the mock executor on a demo
  spec and prints the produced patch/test references and status.

**Out of scope (later changes)**: worklane substrate, async/concurrent dispatch,
retries-as-jobs, Triggerlane bridge, autonomous planning, wiring the executor as
a graph node type (kept as a follow-up once the executor is proven).

## Capabilities

### New Capabilities
- `opencode-executor`: the executor interface and mock, the patch and test
  artifacts a worker produces, and the file-scope guard.

### Modified Capabilities
<!-- None. Reuses artifact-system (store + references) unchanged. -->

## Impact

- **New module** `src/relayflow/executor.py`; reuses the artifact store.
- **New dependency**: optional external `opencode` CLI, invoked only by the real
  executor (never in tests). No new Python dependencies.
- **CLI**: add an `execute` subcommand (mock executor demo).
- **No worklane, no async, no external service required for the test suite.**
