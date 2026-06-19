## 1. Event Bus

- [x] 1.1 Define `Event` (`type`, `payload`) and the `EventBus` protocol
- [x] 1.2 Implement `InMemoryBus` (records events, `subscribe`, `emit`, `receive`)
- [x] 1.3 Add a `TriggerlaneBus` stub (integration-only, not unit-tested)
- [x] 1.4 Tests: subscribed listener receives emitted events; receives externally injected events

## 2. Lifecycle Event Emission

- [x] 2.1 `run_graph` gains an optional `events` bus; emit `node_done` / `node_failed` / `node_blocked`
- [x] 2.2 Ensure behavior and outputs are unchanged when `events` is omitted
- [x] 2.3 Tests: a run with a bus emits a typed event per completed/failed node; without a bus, nothing emitted

## 3. Human Approval Gate

- [x] 3.1 Add `requires_confirmation` to nodes (`add_node` / `add_execution`)
- [x] 3.2 In the scheduler, a confirmation node emits `approval_required` and runs only if `approver(node)` grants it
- [x] 3.3 Denied (or no approver) → node `blocked`, treated as terminal; dependents `blocked`
- [x] 3.4 Tests: approved node runs to `done`; denied node does not run and blocks dependents

## 4. Demo & CLI

- [x] 4.1 Add an approval-gated demo graph and an auto-approver
- [x] 4.2 Add `relayflow approve` CLI running the demo and printing the event log
- [x] 4.3 End-to-end test for the approve command
- [x] 4.4 Run full Definition of Done and confirm green
