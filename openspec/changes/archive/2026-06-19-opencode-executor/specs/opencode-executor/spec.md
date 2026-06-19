## ADDED Requirements

### Requirement: Executor Interface

The system SHALL define an Executor interface that runs an execution spec
(instruction, artifact scope, and allowed paths) and returns a result carrying a
patch, a summary, tests, a status, and the list of touched files. A real
`OpenCodeExecutor` SHALL invoke `opencode run`; a deterministic mock executor
SHALL be provided for tests.

#### Scenario: Mock executor runs a spec and returns a result

- **WHEN** the mock executor runs an execution spec
- **THEN** it SHALL return a result containing `patch`, `summary`, `tests`, `status`, and touched `files`

### Requirement: Patch Artifact

An execution SHALL produce a Patch Artifact whose content is the patch (diff) and
whose metadata carries a `summary`. It SHALL be stored and addressable by
reference.

#### Scenario: Execution produces a referenceable patch artifact

- **WHEN** an in-scope execution completes
- **THEN** a patch artifact of type `patch` SHALL be written to the store
- **AND** its metadata SHALL include the `summary`
- **AND** it SHALL be retrievable by its `artifact://scope/id` reference

### Requirement: Test Artifact

An execution SHALL produce a Test Artifact whose content is the tests and whose
metadata carries a `status` of `passed` or `failed`. It SHALL be stored and
addressable by reference.

#### Scenario: Execution produces a referenceable test artifact

- **WHEN** an in-scope execution completes
- **THEN** a test artifact of type `test` SHALL be written to the store
- **AND** its metadata `status` SHALL be `passed` or `failed`
- **AND** it SHALL be retrievable by its `artifact://scope/id` reference

### Requirement: File Scope Guard

An execution SHALL declare `allowed_paths`. If the produced patch touches any file
outside the allowed paths, the execution SHALL be rejected and SHALL NOT write any
artifact to the store.

#### Scenario: In-scope patch is accepted

- **WHEN** every file touched by the patch is within `allowed_paths`
- **THEN** the execution SHALL write its patch and test artifacts

#### Scenario: Out-of-scope patch is rejected without writing artifacts

- **WHEN** the patch touches a file outside `allowed_paths`
- **THEN** the execution SHALL be rejected with a scope violation
- **AND** no patch or test artifact SHALL be written to the store
