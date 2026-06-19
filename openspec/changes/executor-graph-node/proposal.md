## Why

The Session Graph runs model sessions; the executor runs a real worker. They are
not yet connected. To let the relay drive a worker *as part of a task graph* —
patch/test artifacts flowing as edges, gated before they propagate — a graph node
must be able to run an **execution** as well as a session.

This change generalizes graph nodes to a small work abstraction so session and
execution nodes coexist in one graph, with execution acceptance gated on tests.
Still synchronous, still no worklane.

## What Changes

- Generalize a graph node to wrap a **work** unit (`SessionWork` or
  `ExecutionWork`) exposing `id`, `scope`, `input_refs`, and `output_ref`. The
  public graph API (`add_node`, `roots`, `edges`, `run_graph`, `visualize`) is
  preserved; `add_node(session_input)` keeps working.
- Add **execution nodes**: `add_execution(spec, executor, deps)`. An execution
  node's primary output (its edge to dependents) is the **patch** artifact; it
  also produces the **test** artifact.
- Add **execution acceptance by tests**: an execution node is accepted only when
  its test artifact `status` is `passed`. A failed test or a file-scope violation
  triggers regeneration up to `max_attempts`, then marks the node `failed` (and
  blocks dependents) — the acceptance gate now covers worker output.
- Add a **mixed-graph demo** (session → execution) and a `graph --mixed` CLI flag.

**Out of scope**: worklane / async / concurrency, Triggerlane, autonomous
planning, real `opencode` in tests.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `session-graph`: add the **Execution Node** and **Execution Acceptance by
  Tests** requirements; node identity/edges generalize over session and
  execution work.

## Impact

- **Refactor** `src/relayflow/graph.py`: nodes wrap a `NodeWork` (`SessionWork` /
  `ExecutionWork`); `run_graph` dispatches per work type and gains an optional
  `executor`. Existing session-graph behavior and tests are preserved.
- Reuses `executor.run_execution` (including its scope guard) unchanged.
- **CLI**: `graph --mixed` runs the session→execution demo. No new dependencies.
