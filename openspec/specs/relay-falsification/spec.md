# relay-falsification Specification

## Purpose

Define the self-falsification mechanism: a relay toggle on the same code path,
token metering, an acceptance verdict, and the three-cell experiment matrix that
proves the core bet.

## Requirements

### Requirement: Relay Toggle

The runtime SHALL expose a relay toggle. With relay **on**, a task runs as a
chain of bounded sessions. With relay **off**, the same task runs through the
**same code path** as a degenerate configuration: a single session, a
single-node graph, and an unbounded budget. The toggle SHALL NOT introduce a
separate execution path.

#### Scenario: Relay off is a degenerate single-session run

- **WHEN** a task is run with relay off
- **THEN** the runtime SHALL execute exactly one session with no token ceiling
- **AND** it SHALL use the same assembly and execution code path as relay on

#### Scenario: Relay on chains bounded sessions

- **WHEN** a task is run with relay on
- **THEN** the runtime SHALL execute two or more sessions, each bounded by `budget.max_tokens`

### Requirement: Token Metering

The runtime SHALL measure and report `peak_session_tokens` (the maximum assembled
context across all sessions of a run) and, for a relay-off unbounded run,
`single_shot_tokens` (the context required to run the whole task at once).

#### Scenario: Peak session tokens are reported for a relay run

- **WHEN** a relay-on run completes
- **THEN** the report SHALL include `peak_session_tokens` measured across its sessions

#### Scenario: Single-shot tokens are measured, not estimated

- **WHEN** a relay-off unbounded run completes
- **THEN** the report SHALL include `single_shot_tokens` taken from the actual assembled context

### Requirement: Falsification Experiment Matrix

The runtime SHALL run a three-cell experiment for one task and report the outcome
of each cell: (1) relay off + unbounded, (2) relay off + the bounded budget,
(3) relay on + the same bounded budget.

#### Scenario: Three-cell matrix produces the falsification result

- **WHEN** the experiment matrix is run for a task with a bounded budget B
- **THEN** the report SHALL show cell 1 (relay off, unbounded) completing and yielding `single_shot_tokens`
- **AND** cell 2 (relay off, budget B) SHALL fail or be truncated as not-complete
- **AND** cell 3 (relay on, budget B) SHALL complete with `peak_session_tokens` at or below B

### Requirement: Acceptance Check

A run's task output SHALL be markable as `complete` or `not-complete` by an
explicit acceptance check, so the experiment matrix can compare cells on task
success rather than only on token counts.

#### Scenario: Run outcome carries an acceptance verdict

- **WHEN** a run finishes
- **THEN** its result SHALL carry an acceptance verdict of `complete` or `not-complete`
