## Why

The graph scheduler is synchronous and in-memory: a run that dies loses its
progress, regeneration is a `while` loop, and human approval blocks a live loop
instead of durably parking. To get durability, retry-as-jobs, and real park/
resume — and to lay the exact `Broker` contract that worklane will later fill —
the scheduler needs a durable, broker-driven execution path.

This is **change 1 of 2** for the worklane integration (boundary B). It is
**pure Python**: graph persistence, a `Broker` abstraction with an in-memory
implementation, an idempotent `run-node` step, and one shared execution path for
both synchronous and broker-driven runs. Change 2 (`worklane-broker`) later adds
the worklane-backed `Broker` and the Rust handler shim — the only cross-language
piece — without touching this contract.

## What Changes

- **Persist the graph**: nodes, dependency edges, status, and attempts are stored
  in SQLite so a separate process can load a node, run it, and update its status.
- **`Broker` abstraction**: `enqueue` / `reserve` / `ack` / `retry` /
  `dead_letter` / delayed-enqueue / unique-key dedup, with an `InMemoryBroker`.
  The scheduler depends only on the interface.
- **`WorkerScheduler` over the broker**, plus a **single shared execution path**:
  `run_graph` is reframed to drive the scheduler with an `InMemoryBroker` in
  synchronous mode, reproducing today's fixed-point result. Existing behavior and
  tests are preserved.
- **Idempotent node execution (`relayflow run-node`)** with an atomic
  **CAS-claim** (status `pending`→`running`): a re-delivered or duplicate run of
  an already-claimed/done node is a no-op — at-least-once safety.
- **Retry as jobs**: a rejected node's regeneration is a broker retry with bounded
  attempts; exhaustion routes to dead-letter and marks the node `failed`.
- **Parked approval**: a confirmation-required node is not enqueued until approved;
  an approval enqueues it; denial/timeout leaves it parked (`blocked`).

**Out of scope (change 2)**: the worklane-backed `Broker`, the Rust handler shim,
the dead-letter→failed reconciler against worklane, real concurrency across
processes, worklane lanes. **Also out**: distributed execution, multi-machine.

## Capabilities

### New Capabilities
- `durable-scheduler`: graph persistence, the broker abstraction, the
  broker-driven worker scheduler (shared with the synchronous path), idempotent
  node execution with CAS-claim, retry-as-jobs, and parked approval.

### Modified Capabilities
<!-- None at the spec level. session-graph's guarantees (readiness, acceptance,
     events, approval) are preserved; this adds a durable execution path beneath
     them. The synchronous result of run_graph is unchanged. -->

## Impact

- **New** `src/relayflow/broker.py` (Broker, InMemoryBroker) and graph persistence
  in `graph.py`; new `WorkerScheduler`; `run_graph` reframed onto the broker.
- **CLI**: add `relayflow run-node` (single-node execution) and a durable-run demo.
- **No new dependencies**; pure Python + SQLite. worklane is not required to build
  or test this change.
