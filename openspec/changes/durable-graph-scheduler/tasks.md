## 1. Graph Persistence

- [x] 1.1 Persist nodes (id, work kind + spec), dependency refs, status, attempts to SQLite
- [x] 1.2 Reload a graph by id; round-trip preserves nodes/deps/status/attempts
- [x] 1.3 Durable single-node status update (reload reflects it)
- [x] 1.4 Tests: round-trip, status update durability

## 2. Broker Abstraction

- [x] 2.1 Define `Broker` protocol (`enqueue` with `unique_key`/`delay`, `reserve`, `ack`, `retry`, `dead_letter`)
- [x] 2.2 Implement `InMemoryBroker` (synchronous-capable, unique-key dedup, retry/dead-letter tracking)
- [x] 2.3 Tests: enqueue/reserve payload, unique-key dedup, retry then dead-letter

## 3. Worker Scheduler + Shared Path

- [x] 3.1 Implement `WorkerScheduler`: enqueue ready nodes → reserve → run → enqueue newly-ready dependents
- [x] 3.2 Reframe `run_graph` to drive `WorkerScheduler` with a synchronous `InMemoryBroker`
- [x] 3.3 Confirm ALL existing session-graph / events tests pass unchanged (fixed-point parity)
- [x] 3.4 Tests: completing a node enqueues exactly its newly-ready dependents (no duplicates)

## 4. Idempotent run-node (CAS-claim)

- [x] 4.1 Implement atomic CAS-claim on node status (`pending`→`running`)
- [x] 4.2 Implement `relayflow run-node --graph G --node X` operating on the persisted graph
- [x] 4.3 Re-delivery of a done/claimed node is a no-op; duplicate concurrent claims yield one runner
- [x] 4.4 Tests: duplicate delivery no-op, concurrent-claim single-runner

## 5. Retry As Jobs & Parked Approval

- [x] 5.1 Replace the inner attempts loop with broker retry; exhaustion → dead-letter → node `failed`
- [x] 5.2 Parked approval: confirmation node not enqueued until approved; approval enqueues it; none → `blocked`
- [x] 5.3 Tests: transient rejection retried then accepted; exhausted → failed+blocked; approval enqueues parked node

## 6. Demo & CLI

- [x] 6.1 Add a durable-run demo (persisted graph + run-node + scheduler) over the in-memory broker
- [x] 6.2 Wire CLI (`run-node`, and a durable graph run) and an end-to-end test
- [x] 6.3 Run full Definition of Done and confirm green
