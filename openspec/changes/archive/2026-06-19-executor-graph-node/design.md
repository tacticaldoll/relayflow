## Context

`graph.py` nodes wrap a `SessionInput` and `run_graph` calls `run_session`
directly. To let executions be nodes, the node must abstract over "a unit of work
that, when run, produces a primary output artifact and can be judged accepted."
This is a focused refactor that preserves the existing public API and behavior.

## Goals / Non-Goals

**Goals:**
- A `NodeWork` abstraction with `SessionWork` and `ExecutionWork`.
- Execution nodes producing patch + test artifacts, edge = patch ref.
- Acceptance: session via the pluggable acceptor (unchanged), execution via test
  status `passed`.
- Preserve `add_node(session_input)`, `roots`, `edges`, `run_graph`, `visualize`.

**Non-Goals:**
- worklane / async / concurrency / retries-as-jobs.
- Real `opencode` execution in tests; autonomous planning; Triggerlane.

## Decisions

- **`NodeWork` protocol**: `id`, `scope`, `input_refs`, `output_ref`, plus
  `run(store, llm, executor, sessions)` and `accepted(store, acceptor)`. `GraphNode`
  holds a `work` and the scheduler is work-agnostic — it computes readiness from
  `input_refs`/`output_ref` and calls `work.run` / `work.accepted`.
- **Backward-compatible construction**: `add_node(session_input)` wraps a
  `SessionWork` (so existing callers and tests are unchanged); `add_execution(spec,
  executor, deps)` wraps an `ExecutionWork`.
- **Execution primary output = patch ref** (`{id}.patch`). Dependents reference the
  patch; the test artifact (`{id}.test`) is the acceptance signal, not an edge.
- **Acceptance split by work type.** `SessionWork.accepted` = `acceptor(out)`
  (default accept-all, preserves V1 behavior). `ExecutionWork.accepted` = test
  `status == "passed"`. The `acceptor` argument keeps governing session nodes.
- **Scope violation is caught, not fatal.** `ExecutionWork.run` catches
  `FileScopeViolation` so a bad patch fails the attempt (and ultimately the node)
  rather than crashing the scheduler — consistent with regeneration semantics.

## Risks / Trade-offs

- **Refactor touches core `graph.py`** → the public API and the existing
  session-graph tests are the contract; they must stay green, which pins behavior.
- **Two artifacts, one edge** → only the patch is an edge; tests are a side signal.
  Documented so dependents don't accidentally depend on `{id}.test`.
- **Deterministic regeneration can't fix a failing test** → bounded attempts then
  `failed`; tests use an executor whose status flips to exercise the accept path.
