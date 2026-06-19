# durable-scheduler Specification

## Purpose

Make the graph durable and broker-driven: persist the graph so a separate process
can run a node, define the `Broker` contract worklane will later fill, and run
both the synchronous and broker-driven paths through one scheduler with idempotent
node execution, retry-as-jobs, and durable parked approval.

## Requirements

### Requirement: Graph Persistence

A graph SHALL be persistable to a store, recording each node's identity,
dependency references, status, and attempt count, and SHALL be reloadable by a
graph id. A separate process SHALL be able to load a node, run it, and update its
status through the persisted graph.

#### Scenario: A graph round-trips through the store

- **WHEN** a graph with nodes, dependencies, and statuses is persisted and reloaded by id
- **THEN** the reloaded graph SHALL expose the same nodes, dependencies, statuses, and attempt counts

#### Scenario: A node status update is durable

- **WHEN** a node's status is updated and the graph is reloaded
- **THEN** the reloaded node SHALL carry the updated status

### Requirement: Broker Abstraction

The system SHALL define a `Broker` interface supporting `enqueue`, `reserve`,
`ack`, `retry`, `dead_letter`, delayed enqueue, and unique-key deduplication, with
an in-memory implementation. The scheduler SHALL depend only on the interface.

#### Scenario: Enqueue and reserve a job

- **WHEN** a job is enqueued and then reserved
- **THEN** the reserved job SHALL carry the enqueued payload

#### Scenario: Unique-key deduplication

- **WHEN** two jobs are enqueued with the same unique key
- **THEN** the broker SHALL hold only one job for that key

### Requirement: Worker Scheduler With Shared Path

A `WorkerScheduler` SHALL drive a graph by enqueuing ready nodes, reserving jobs,
running them, and enqueuing newly-ready dependents. The existing synchronous
`run_graph` SHALL be reframed to drive this scheduler with the in-memory broker in
synchronous mode and SHALL produce the same fixed-point result as before.

#### Scenario: Synchronous run reaches the same fixed point

- **WHEN** a graph is run via the synchronous path
- **THEN** the resulting node statuses SHALL match the pre-existing synchronous scheduler's result

#### Scenario: Completing a node enqueues its newly-ready dependents

- **WHEN** a node completes and is accepted
- **THEN** the scheduler SHALL enqueue each dependent whose inputs are now all present and accepted

### Requirement: Idempotent Node Execution

Running a node SHALL atomically claim it by a compare-and-set on status
(`pending`→`running`). A run delivered for a node that is already claimed or
already `done` SHALL be a no-op. Node execution SHALL be exposed as a
`relayflow run-node` command operating on the persisted graph.

#### Scenario: A duplicate delivery does not run the work twice

- **WHEN** a node that is already `done` receives another run delivery
- **THEN** the run SHALL be a no-op and SHALL NOT re-run the work

#### Scenario: Concurrent claims yield a single runner

- **WHEN** two runs attempt to claim the same `pending` node
- **THEN** only one SHALL win the claim and run the work; the other SHALL yield

### Requirement: Retry As Jobs

A rejected node SHALL be regenerated as a broker retry with a bounded number of
attempts. When attempts are exhausted, the job SHALL be routed to the dead-letter
path and the node SHALL be marked `failed`, blocking its dependents.

#### Scenario: A transient rejection is retried then accepted

- **WHEN** a node's output is rejected once and then accepted on retry
- **THEN** the node SHALL end `done` after the retry

#### Scenario: Exhausted retries dead-letter and fail the node

- **WHEN** a node's output is rejected on every allowed attempt
- **THEN** the job SHALL be dead-lettered
- **AND** the node SHALL be marked `failed` and its dependents `blocked`

### Requirement: Parked Approval

A node requiring confirmation SHALL NOT be enqueued until approved. An approval
SHALL enqueue the node; a denial or timeout SHALL leave the node parked and
`blocked`. Parking SHALL be durable, not a blocked in-process loop.

#### Scenario: Approval enqueues a parked node

- **WHEN** a confirmation-required node is parked and an approval arrives
- **THEN** the node SHALL be enqueued and SHALL run

#### Scenario: Without approval the node stays parked

- **WHEN** a confirmation-required node receives no approval
- **THEN** the node SHALL remain parked and `blocked`, with no work run

### Requirement: Graph Inspect

The system SHALL render a persisted graph read-only by its graph id, showing its
nodes, statuses, and edges. Graph inspect SHALL NOT run the model or mutate the
graph.

#### Scenario: Inspect renders a persisted graph

- **WHEN** a persisted graph is inspected by its id
- **THEN** the output SHALL show the graph's nodes with their stored statuses and the edges between them
- **AND** no model call SHALL be issued and no status SHALL change

#### Scenario: Inspecting an unknown graph id reports not found

- **WHEN** a graph id that was never persisted is inspected
- **THEN** the command SHALL exit non-zero with a not-found message
