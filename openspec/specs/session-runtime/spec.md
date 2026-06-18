# session-runtime Specification

## Purpose

Define the context-bounded unit of LLM work — its inputs, output contract,
persistence (without reasoning), and read-only trace inspection.

## Requirements

### Requirement: Session Definition

A Session SHALL be a context-bounded unit of LLM work, defined by the fields
`id`, `purpose`, `context`, `constraints`, and `budget`. The `budget` SHALL carry
a `max_tokens` ceiling that bounds the assembled context for that session.

#### Scenario: Session is created with required fields

- **WHEN** a session is created with `id`, `purpose`, `context`, `constraints`, and `budget`
- **THEN** the runtime SHALL accept it and expose those fields unchanged for execution

#### Scenario: Session without a token budget is rejected

- **WHEN** a session is created without a `budget.max_tokens` value
- **THEN** the runtime SHALL reject the session with a validation error

### Requirement: Session Output Contract

A completed Session SHALL produce a structured output containing `summary`,
`artifacts`, and `next_actions`. `artifacts` SHALL be references to stored
artifacts, not inline content.

#### Scenario: Session produces the output contract

- **WHEN** a session completes successfully
- **THEN** its output SHALL contain `summary`, `artifacts`, and `next_actions`
- **AND** each entry in `artifacts` SHALL be an `artifact://scope/id` reference

### Requirement: Session Persistence Without Reasoning

The runtime SHALL persist each session's `input`, `output`, and produced
`artifact` references. It SHALL NOT persist the model's full chain-of-thought
or intermediate reasoning.

#### Scenario: Input, output and artifacts are persisted

- **WHEN** a session completes
- **THEN** the store SHALL contain its `input`, `output`, and artifact references retrievable by session id

#### Scenario: Full reasoning is not persisted

- **WHEN** a persisted session is read back
- **THEN** the record SHALL NOT contain the model's full intermediate reasoning trace

### Requirement: Session Inspect

The CLI SHALL provide `relayflow inspect <session-id>` that replays the recorded
input/output trace of a session. Inspect SHALL be a read-only trace replay and
SHALL NOT re-execute the session against the model.

#### Scenario: Inspect replays a recorded session

- **WHEN** the user runs `relayflow inspect <session-id>` for a persisted session
- **THEN** the CLI SHALL display the recorded input, output, and artifact references
- **AND** it SHALL NOT issue any new model call

#### Scenario: Inspect on an unknown session id

- **WHEN** the user runs `relayflow inspect <session-id>` for an id that does not exist
- **THEN** the CLI SHALL exit with a non-zero status and a not-found message
