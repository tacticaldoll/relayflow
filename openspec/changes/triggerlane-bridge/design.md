## Context

RelayFlow needs to report lifecycle events to an external layer (Triggerlane) and
to pause for a human before sensitive nodes. This adds an event bus and an
approval gate to the synchronous graph run, behind a mockable bus.

## Goals / Non-Goals

**Goals:**
- An `Event`/`EventBus` with `InMemoryBus` (test) and a `TriggerlaneBus` stub.
- Graph run emits node lifecycle + approval events onto an optional bus.
- Listeners subscribe and receive emitted/injected events.
- `requires_confirmation` nodes run only on approval; denial blocks them.

**Non-Goals:**
- worklane / async / scheduled-delayed park-resume; real Triggerlane transport.
- Changing existing graph behavior when no bus/approver is supplied.

## Decisions

- **Approval is a synchronous decision point.** The scheduler, on reaching a
  ready node that `requires_confirmation`, emits `approval_required` and calls
  `approver(node) -> bool`. Granted → run as normal (acceptance/regeneration
  unchanged); denied → node `blocked` immediately and treated as terminal so it is
  not reconsidered. This is the faithful synchronous rendering of "park for a
  human"; real async park/resume (delayed enqueue) is a worklane change.
- **No approver + requires_confirmation = denied.** A confirmation-gated node with
  no approver cannot proceed, so it ends `blocked` — fail safe, not fail open.
- **Events are optional and side-effect-only.** `run_graph` takes `events=None`;
  when present it emits `node_done` / `node_failed` / `node_blocked` and the
  approval events. With no bus, behavior and outputs are identical to before.
- **Bus is bidirectional via one path.** `emit` records and dispatches to
  listeners (outbound, RelayFlow→world). `receive` dispatches an externally
  injected event to listeners (inbound, world→RelayFlow). The same listener list
  serves both, so a Triggerlane report and a local emission look the same to
  subscribers.
- **`requires_confirmation` lives on the node**, set at `add_node` /
  `add_execution`. It is orthogonal to the work type.

## Risks / Trade-offs

- **Denied-as-blocked conflates "needs human later" with "rejected"** → V1 keeps
  one terminal `blocked` state; resumable parking is deferred to worklane, where a
  delayed re-enqueue can revisit the decision.
- **Event emission threading through the scheduler** → kept to a few well-defined
  points (node terminal status + approval), so the run loop stays readable.
- **Stub `TriggerlaneBus`** is integration-only and untested by the suite; the
  contract everything depends on is `EventBus`, so the real transport drops in
  later without touching the graph.
