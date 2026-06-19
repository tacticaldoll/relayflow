## 1. Executor Interface

- [x] 1.1 Define `ExecSpec` (id, scope, instruction, allowed_paths) and `ExecResult` (patch, summary, tests, status, files)
- [x] 1.2 Define the `Executor` protocol and a deterministic `MockExecutor`
- [x] 1.3 Implement `OpenCodeExecutor` that shells `opencode run` and populates `ExecResult` (integration-only, not unit-tested)
- [x] 1.4 Tests: mock executor returns patch/summary/tests/status/files

## 2. Patch & Test Artifacts

- [x] 2.1 Implement `run_execution(store, executor, spec)` writing a patch artifact (`{id}.patch`, type `patch`, metadata summary+files)
- [x] 2.2 Write a test artifact (`{id}.test`, type `test`, metadata status)
- [x] 2.3 Return the patch and test references; both resolvable from the store
- [x] 2.4 Tests: patch and test artifacts are written, typed, and resolvable by reference

## 3. File Scope Guard

- [x] 3.1 Implement path-prefix scope check (`files` within `allowed_paths`)
- [x] 3.2 Reject out-of-scope execution with `FileScopeViolation` and write no artifacts
- [x] 3.3 Tests: in-scope writes artifacts; out-of-scope raises and store stays empty

## 4. Demo & CLI

- [x] 4.1 Add a demo spec + mock executor producing an in-scope patch/test
- [x] 4.2 Add a `relayflow execute` CLI subcommand printing patch/test refs and status
- [x] 4.3 End-to-end test for the CLI execute path
- [x] 4.4 Run full Definition of Done and confirm green
