## 1. Visualizer Upgrade

- [ ] 1.1 Add `kind` to `NodeWork` (`SessionWork`→"session", `ExecutionWork`→"execution")
- [ ] 1.2 Upgrade `visualize`: status summary line; node lines with kind; edge lines annotated with the carried artifact reference (keep existing substrings)
- [ ] 1.3 Tests: kind shown per node; edge shows artifact ref; existing visualize assertions still hold

## 2. Read-only Graph Load

- [ ] 2.1 Allow loading execution nodes without a live executor (render-only); `ExecutionWork.executor` optional
- [ ] 2.2 Add `GraphStore.exists(graph_id)`
- [ ] 2.3 Tests: load persisted graph (incl. execution node) with no executor renders

## 3. Durable run-node + Graph Inspect CLI

- [ ] 3.1 `run-node --db <file>`: persist graph only if absent (preserve statuses across invocations); in-memory when no `--db`
- [ ] 3.2 `inspect --graph <id> --db <file>`: load persisted graph and render via the upgraded visualizer; no model call
- [ ] 3.3 Unknown graph id → non-zero exit + not-found message
- [ ] 3.4 Tests: run-node twice on a file db accumulates done status; inspect --graph renders it; unknown-id error path

## 4. Definition of Done

- [ ] 4.1 Run full Definition of Done and confirm green
