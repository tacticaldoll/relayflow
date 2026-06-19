## 1. Work Abstraction

- [x] 1.1 Define `NodeWork` protocol (`id`, `scope`, `input_refs`, `output_ref`, `run`, `accepted`)
- [x] 1.2 Implement `SessionWork` wrapping `SessionInput` (output `{id}.out`, accepted via acceptor)
- [x] 1.3 Refactor `GraphNode` to hold a `work`; keep `id`/`output_ref`/`input_refs`/`status`/`attempts`
- [x] 1.4 Keep `SessionGraph.add_node(session_input)` wrapping `SessionWork`; update `run_graph` to dispatch via `work`
- [x] 1.5 Confirm all existing session-graph tests still pass unchanged

## 2. Execution Node

- [x] 2.1 Implement `ExecutionWork` wrapping `ExecSpec`+`Executor`+`deps` (output `{id}.patch`, also produces `{id}.test`)
- [x] 2.2 `ExecutionWork.run` calls `run_execution`, catching `FileScopeViolation` as a non-fatal failed attempt
- [x] 2.3 `ExecutionWork.accepted` returns true iff the test artifact `status` is `passed`
- [x] 2.4 Add `SessionGraph.add_execution(spec, executor, deps)`
- [x] 2.5 Tests: execution node writes patch+test, edge is the patch ref, session can depend on a patch

## 3. Acceptance Semantics

- [x] 3.1 Tests: passing tests → node `done`; failing tests every attempt → `failed` + dependents `blocked`
- [x] 3.2 Tests: file-scope violation → not accepted (node `failed`, nothing propagates)

## 4. Demo & CLI

- [x] 4.1 Add a mixed-graph demo builder (session "plan" → execution "impl")
- [x] 4.2 Add `relayflow graph --mixed` to run and visualize the mixed graph
- [x] 4.3 End-to-end test: mixed graph runs to all `done`, patch + test artifacts present
- [x] 4.4 Run full Definition of Done and confirm green
