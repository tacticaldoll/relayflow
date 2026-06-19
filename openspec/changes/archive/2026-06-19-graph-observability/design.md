## Context

The graph is durable (GraphStore) but hard to see: `visualize` is minimal and
`inspect` only reads sessions. This adds richer rendering and a graph-level
read-only inspect, reusing the upgraded visualizer.

## Goals / Non-Goals

**Goals:**
- Visualizer shows node kind + per-edge artifact reference; keeps existing
  substrings so current tests/CLI output stay valid.
- Durable `run-node --db`: persist-once, preserve statuses across invocations.
- `inspect --graph <id> --db <file>`: read-only render of a persisted graph.

**Non-Goals:**
- Graphical/HTML/streaming views; inspecting artifact contents (session inspect
  already does session I/O).

## Decisions

- **Backward-compatible visualizer.** Keep the `id [status]` token and
  `producer -> consumer` line; append ` (kind)` to node lines and ` [artifact-ref]`
  to edge lines, plus a leading one-line status summary. Existing assertions and
  CLI output remain valid; new detail is additive.
- **Node kind via `NodeWork.kind`.** `SessionWork.kind = "session"`,
  `ExecutionWork.kind = "execution"`. The visualizer reads it instead of
  isinstance-checking, keeping rendering decoupled from work types.
- **Edge artifact = producer's `output_ref`.** An edge exists because the consumer
  references the producer's output; that reference is what the edge "carries".
- **Durable run-node.** `run-node --db` persists the demo graph only if absent
  (`GraphStore.exists`), so node statuses set by prior runs survive; without `--db`
  it stays in-memory (current behavior preserved).
- **Graph inspect is read-only.** It loads via `GraphStore.load_graph` and renders;
  it constructs no llm/executor and updates no status — structurally guaranteeing
  "no model call", matching session inspect's contract. Execution nodes render
  without needing an executor (rendering only reads spec/status, not runtime deps).

## Risks / Trade-offs

- **Execution-node load needs an executor** (to rebuild `ExecutionWork`) → graph
  inspect only renders, so it loads with a lightweight rendering view that does not
  require the executor; the loader tolerates a missing executor for read-only use.
- **Shared db file for ArtifactStore + GraphStore** → distinct tables, same file;
  already how `run-node` works. Documented so the `--db` is understood as one store.
