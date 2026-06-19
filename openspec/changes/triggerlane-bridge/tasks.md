## 1. Event Bus

- [ ] 1.1 Define `Event` (`type`, `payload`) and the `EventBus` protocol
- [ ] 1.2 Implement `InMemoryBus` (records events, `subscribe`, `emit`, `receive`)
- [ ] 1.3 Add a `TriggerlaneBus` stub (integration-only, not unit-tested)
- [ ] 1.4 Tests: subscribed listener receives emitted events; receives externally injected events

## 2. Lifecycle Event Emission

- [ ] 2.1 `run_graph` gains an optional `events` bus; emit `node_done` / `node_failed` / `node_blocked`
- [ ] 2.2 Ensure behavior and outputs are unchanged when `events` is omitted
- [ ] 2.3 Tests: a run with a bus emits a typed event per completed/failed node; without a bus, nothing emitted

## 3. Human Approval Gate

- [ ] 3.1 Add `requires_confirmation` to nodes (`add_node` / `add_execution`)
- [ ] 3.2 In the scheduler, a confirmation node emits `approval_required` and runs only if `approver(node)` grants it
- [ ] 3.3 Denied (or no approver) → node `blocked`, treated as terminal; dependents `blocked`
- [ ] 3.4 Tests: approved node runs to `done`; denied node does not run and blocks dependents

## 4. Demo & CLI

- [ ] 4.1 Add an approval-gated demo graph and an auto-approver
- [ ] 4.2 Add `relayflow approve` CLI running the demo and printing the event log
- [ ] 4.3 End-to-end test for the approve command
- [ ] 4.4 Run full Definition of Done and confirm green
