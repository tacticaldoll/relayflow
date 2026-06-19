## ADDED Requirements

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
