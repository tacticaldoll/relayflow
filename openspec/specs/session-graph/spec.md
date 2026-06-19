# session-graph Specification

## Purpose

Generalize the linear relay into a DAG: sessions as nodes, artifacts as edges,
advanced by a synchronous readiness scheduler and guarded by an acceptance gate
so a bad artifact cannot propagate down the chain.

## Requirements

### Requirement: Graph Node

A Graph Node SHALL wrap a single session input and carry a status derived from
the graph state, one of: `pending`, `ready`, `running`, `done`, `blocked`, or
`failed`. Each node SHALL be identified by its session id.

#### Scenario: A node wraps a session and starts pending

- **WHEN** a node is added to a graph for a session input
- **THEN** the node SHALL be identified by the session id
- **AND** its initial status SHALL be `pending`

### Requirement: Graph Edge

A Graph Edge SHALL express an artifact dependency: a node depends on one or more
input artifact references. A node's dependencies are the artifact references its
session input declares.

#### Scenario: An edge links a producer artifact to a consumer node

- **WHEN** node B declares an input reference produced by node A
- **THEN** the graph SHALL record an edge from A's artifact to B
- **AND** B SHALL depend on that artifact reference

### Requirement: Artifact Acceptance Gate

A produced artifact SHALL be passed through an acceptance gate that marks it
`accepted` or `rejected`. A rejected artifact SHALL cause its producing node to
re-generate, up to a bounded number of attempts. Downstream nodes SHALL remain
blocked until every input artifact they depend on is accepted.

#### Scenario: An accepted artifact unblocks dependents

- **WHEN** a node produces an artifact and the gate accepts it
- **THEN** that artifact SHALL be marked accepted
- **AND** nodes depending only on accepted artifacts SHALL become eligible to run

#### Scenario: A rejected artifact triggers regeneration

- **WHEN** the gate rejects a node's produced artifact
- **THEN** the node SHALL re-run to regenerate the artifact
- **AND** its dependents SHALL stay blocked while the artifact is not accepted

#### Scenario: Exhausting attempts fails the node

- **WHEN** a node's artifact is rejected on every allowed attempt
- **THEN** the node SHALL be marked `failed`
- **AND** its dependents SHALL be marked `blocked`

### Requirement: Readiness Scheduler

The scheduler SHALL run nodes in dependency order. A node SHALL be `ready` only
when all of its input artifacts exist and are accepted. The ready set SHALL be
computed as a projection of graph and artifact state, not held as a separate
persisted queue. The scheduler SHALL run ready nodes until none remain ready.

#### Scenario: Nodes run only after their inputs are accepted

- **WHEN** the scheduler ticks and a node's inputs are all present and accepted
- **THEN** the scheduler SHALL run that node
- **AND** a node with an unmet or unaccepted input SHALL NOT be run

#### Scenario: A diamond graph completes in dependency order

- **WHEN** a graph has a root, two independent middle nodes depending on it, and a sink depending on both
- **THEN** the scheduler SHALL run the root first, then the two middle nodes, then the sink
- **AND** all nodes SHALL end with status `done`

#### Scenario: Ready set is derived, not stored

- **WHEN** the scheduler determines which nodes are ready
- **THEN** readiness SHALL be derived from node statuses and artifact acceptance at that moment

### Requirement: Human-Controlled Next Sessions

Nodes and edges SHALL be added to a graph explicitly by the caller. The graph
SHALL NOT generate next sessions autonomously from model output in this version.

#### Scenario: Caller adds the next node explicitly

- **WHEN** the caller adds a node and declares its input references
- **THEN** the graph SHALL incorporate it without invoking a model to plan it

### Requirement: Graph Visualizer

The system SHALL render a graph as readable text showing nodes, their statuses,
and the edges between them.

#### Scenario: Visualize renders nodes, statuses and edges

- **WHEN** a graph is visualized
- **THEN** the output SHALL list each node with its status
- **AND** it SHALL show the dependency edges between nodes

### Requirement: Execution Node

A graph node SHALL be able to run an execution (a worker) instead of a session.
An execution node SHALL produce a patch artifact and a test artifact; its
**primary output** for edge derivation SHALL be the patch artifact reference.
Session and execution nodes SHALL coexist in one graph, with edges derived
uniformly from input references.

#### Scenario: An execution node produces patch and test artifacts

- **WHEN** an execution node runs in a graph
- **THEN** it SHALL write a patch artifact and a test artifact to the store
- **AND** its primary output reference SHALL be the patch artifact

#### Scenario: A session node depends on an execution node's patch

- **WHEN** a session node declares an input reference to an execution node's patch artifact
- **THEN** the graph SHALL record an edge from the execution node to the session node
- **AND** the session node SHALL run only after the execution node is accepted

### Requirement: Execution Acceptance by Tests

An execution node SHALL be accepted only when its test artifact `status` is
`passed`. A failed test or a file-scope violation SHALL be treated as not
accepted, triggering regeneration up to the allowed attempts; if still not
accepted, the node SHALL be marked `failed` and its dependents `blocked`.

#### Scenario: Passing tests accept the execution node

- **WHEN** an execution node's tests report `passed`
- **THEN** the node SHALL be marked `done`
- **AND** its patch artifact SHALL be available to dependents

#### Scenario: Failing tests block the execution node

- **WHEN** an execution node's tests report `failed` on every allowed attempt
- **THEN** the node SHALL be marked `failed`
- **AND** its dependents SHALL be marked `blocked`

#### Scenario: A file-scope violation is not accepted

- **WHEN** an execution node's patch is rejected by the file-scope guard
- **THEN** the node SHALL NOT be accepted
- **AND** no patch or test artifact from that attempt SHALL propagate to dependents
