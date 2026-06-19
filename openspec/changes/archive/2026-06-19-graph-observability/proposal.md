## Why

The graph is now durable, but observability lags: `visualize` shows only node id +
status and bare edges, and `relayflow inspect` only reads a single persisted
session — there is no way to see a persisted *graph*. This change makes graph
state legible: a richer visualizer and a graph-level `inspect` that renders a
persisted graph read-only.

## What Changes

- **Upgrade `visualize`**: each node line shows its **kind** (`session` /
  `execution`) alongside status; each edge shows the **artifact reference** it
  carries; a one-line status summary is added. Existing substrings
  (`id [status]`, `producer -> consumer`) are preserved.
- **`run-node --db <file>` becomes durable**: the demo graph is persisted to the
  file once and node statuses are preserved across invocations (no re-save that
  resets status), so runs accumulate.
- **`inspect --graph <id> --db <file>`**: load a persisted graph from the
  `GraphStore` and render it via the upgraded visualizer. Read-only, **no model
  call** — consistent with session inspect.

**Out of scope**: graphical/HTML rendering, live/streaming views, inspecting
artifact contents (session inspect already covers session I/O).

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `session-graph`: the **Graph Visualizer** requirement is upgraded to include
  node kind and per-edge artifact references.
- `durable-scheduler`: add a **Graph Inspect** requirement — render a persisted
  graph read-only without running the model.

## Impact

- `src/relayflow/graph.py`: `NodeWork.kind`; richer `visualize`.
- `src/relayflow/graphstore.py`: an `exists(graph_id)` check + a graph-inspect
  render helper.
- `src/relayflow/cli.py`: `run-node --db` durability; `inspect --graph`.
- No new dependencies. Session inspect and existing visualize substrings unchanged.
