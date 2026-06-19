## Context

This is change 1 of 2 for the worklane integration (boundary B). It makes the
graph durable and broker-driven in pure Python, defining the `Broker` contract
worklane will later implement. The synchronous `run_graph` is preserved by
reframing it onto the same broker-driven path with an in-memory broker.

## Goals / Non-Goals

**Goals:**
- Persist the graph (nodes/edges/status/attempts) so a separate process runs a node.
- A `Broker` interface + `InMemoryBroker`; the scheduler depends only on it.
- One shared execution path; `run_graph`'s synchronous result is unchanged.
- Idempotent `run-node` via CAS-claim; retry-as-jobs; durable parked approval.

**Non-Goals:**
- The worklane-backed broker, the Rust handler shim, real cross-process
  concurrency, worklane lanes, dead-letter reconciliation against worklane —
  all change 2.
- Distributed/multi-machine execution.

## Decisions

- **One shared path (option 3).** A single `WorkerScheduler` drives the graph over
  a `Broker`. `run_graph` becomes a thin wrapper: build an `InMemoryBroker` in
  synchronous mode, run the scheduler to a fixed point, return the same
  `GraphRunResult`. Two loops cannot drift because there is one loop. The
  acceptance test for this change is: every existing session-graph test passes
  unchanged.
- **CAS-claim for idempotency (option 2).** A node is run only after an atomic
  status transition `pending`→`running` (a conditional SQLite UPDATE). A delivery
  for an already-`running`/`done` node is a no-op. This makes at-least-once
  delivery safe and is also the foundation for future concurrency. Chosen over
  "rely on idempotent writes" because executor work mutates files and must not be
  applied twice.
- **Broker contract mirrors worklane's lifecycle** so change 2 is a drop-in:
  `enqueue(payload, unique_key=None, delay=None)`, `reserve()`, `ack(job)`,
  `retry(job)`, `dead_letter(job)`. The job payload is the thin envelope
  `{graph_id, node_id}` — never business truth.
- **Newly-ready computed in Python after each completion.** On accept, the runner
  recomputes which dependents are now ready (all inputs present + accepted) and
  enqueues them with `unique_key=node_id` to prevent double-enqueue. Readiness is
  still a projection of graph + artifact state.
- **Retry-as-jobs replaces the inner attempts loop.** A rejected run calls
  `broker.retry(job)`; the broker re-delivers up to `max_attempts`; on exhaustion
  it `dead_letter`s and the runner marks the node `failed`.
- **Parked approval = not enqueued.** A confirmation-required node is held (not
  enqueued) and emits `approval_required`; an approval enqueues it. In synchronous
  mode the `approver` is consulted inline (preserving current behavior); in broker
  mode the approval is an external enqueue trigger. Timeout maps to a delayed
  enqueue (carried, exercised fully in change 2).

## Risks / Trade-offs

- **Reframing `run_graph` risks behavior drift** → the existing 66 tests are the
  contract and must stay green; the synchronous in-memory broker must reproduce
  the exact fixed-point, acceptance, regeneration, and approval semantics.
- **Graph persistence adds a second source of state next to artifacts** → status/
  attempts are execution state; truth about *outputs* remains the artifact store.
  `run-node` always re-derives "done?" from status+artifact, never from a queue.
- **CAS-claim correctness under the in-memory broker is only a model** of the real
  concurrent case → change 2's worklane backend is where true concurrency is
  exercised; here CAS is validated by simulating duplicate deliveries.
- **Scope of one change is large** (persistence + broker + scheduler refactor) →
  tasks are ordered so the synchronous path is reproduced first (lowest risk),
  then retry/park are layered on.
