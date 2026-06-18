## 1. Graph Model

- [x] 1.1 Define `GraphNode` wrapping a `SessionInput` with derived status (`pending`/`ready`/`running`/`done`/`blocked`/`failed`)
- [x] 1.2 Define `SessionGraph` with explicit `add_node` and dependency edges derived from each node's input references
- [x] 1.3 Implement edge/producer resolution: map an input ref to the producing node (`{node_id}.out`); roots have no inbound edges
- [x] 1.4 Tests: node starts pending, edges link producer→consumer, roots identified

## 2. Acceptance Gate

- [x] 2.1 Define a pluggable acceptor predicate `accept(artifact) -> bool` (default accept-all) and per-ref acceptance tracking
- [x] 2.2 Implement regeneration: rejected artifact re-runs its node up to `max_attempts`, then marks the node `failed`
- [x] 2.3 Tests: accepted artifact unblocks dependents; rejected triggers re-run; exhausted attempts → `failed` + dependents `blocked`

## 3. Scheduler

- [x] 3.1 Implement readiness: a node is `ready` when all input artifacts exist and are accepted; ready set derived each tick (no stored queue)
- [x] 3.2 Implement the synchronous run loop: run ready nodes (with acceptance + regeneration) until none remain ready; report blocked remainder
- [x] 3.3 Tests: nodes run only after inputs accepted; diamond graph completes in order all `done`; stuck graph stops with `blocked`

## 4. Construction & Visualization

- [x] 4.1 Confirm nodes/edges are added explicitly by the caller (no model-driven planning) and cover it with a test
- [x] 4.2 Implement a text graph visualizer (nodes + statuses + edges)
- [x] 4.3 Tests: visualizer lists nodes with status and shows edges

## 5. Demo & CLI

- [x] 5.1 Build a demo graph from the marker task decomposition (extract nodes → synthesis sink)
- [x] 5.2 Add a `relayflow graph` CLI subcommand that runs the demo graph and prints the visualization
- [x] 5.3 End-to-end test: demo graph runs to all `done` and the synthesis artifact is complete
- [x] 5.4 Run full Definition of Done and confirm green
