## Why

RelayFlow should be decoupled from the execution/reporting layer and able to
pause for a human before a sensitive step. Triggerlane is the event layer; this
change adds the bridge: emit lifecycle events, let listeners receive them, and
gate selected graph nodes behind human approval.

Synchronous and behind a mockable bus (mirroring `LLMClient`/`Executor`), so the
suite runs without Triggerlane. True async park/resume (scheduled/delayed
enqueue) remains a worklane concern.

## What Changes

- Add an **Event** (`type`, `payload`) and an **EventBus** interface with an
  `InMemoryBus` for tests and a `TriggerlaneBus` stub (integration-only).
- **Emit lifecycle events** from a graph run: node done/failed/blocked and the
  approval events below, onto an optional bus.
- **Event listeners**: handlers subscribe to the bus and are invoked when events
  occur, so an external system (Triggerlane) can observe and report back.
- **Human approval** (`requires_confirmation`): a node marked for confirmation
  emits `approval_required` and runs only if an approver grants it; a denial
  blocks the node (and its dependents) without running it. The decision comes
  from outside the model.
- Add an approval demo and a `relayflow approve` CLI command that runs an
  approval-gated graph and prints the event log.

**Out of scope**: worklane / async / scheduled-delayed park-resume, real
Triggerlane transport, autonomous planning.

## Capabilities

### New Capabilities
- `triggerlane-bridge`: event emit, event listener, and human approval gating of
  graph nodes.

### Modified Capabilities
<!-- None at the spec level. The graph gains optional event emission and an
     approval gate as implementation of the bridge requirements. -->

## Impact

- **New module** `src/relayflow/events.py` (Event, EventBus, InMemoryBus,
  TriggerlaneBus stub).
- **Graph**: `run_graph` gains optional `events` and `approver`; nodes gain
  `requires_confirmation`. Existing behavior unchanged when both are omitted.
- **CLI**: add an `approve` subcommand. No new Python dependencies.
