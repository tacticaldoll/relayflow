# triggerlane-bridge Specification

## Purpose

Decouple RelayFlow from the execution/reporting layer: emit lifecycle events onto
a bus that listeners (Triggerlane) can observe, and gate selected graph nodes
behind human approval.

## Requirements

### Requirement: Event Emit

The runtime SHALL emit lifecycle events, each with a `type` and a `payload`, onto
an event bus when one is provided. A graph run SHALL emit an event when a node
completes, fails, or is blocked.

#### Scenario: A graph run emits node lifecycle events

- **WHEN** a graph runs with an event bus provided
- **THEN** the bus SHALL receive an event for each node that completes or fails
- **AND** each event SHALL carry a `type` and a `payload` identifying the node

#### Scenario: No bus means no emission requirement

- **WHEN** a graph runs without an event bus
- **THEN** the run SHALL behave exactly as before, emitting nothing

### Requirement: Event Listener

The event bus SHALL allow listeners to subscribe. When an event is emitted or an
external event is received, every subscribed listener SHALL be invoked with that
event.

#### Scenario: A subscribed listener receives emitted events

- **WHEN** a listener is subscribed and an event is emitted
- **THEN** the listener SHALL be invoked with that event

#### Scenario: A listener receives an externally injected event

- **WHEN** an external event (e.g. a Triggerlane report) is received by the bus
- **THEN** every subscribed listener SHALL be invoked with that event

### Requirement: Human Approval

A node that is marked as requiring confirmation SHALL emit an `approval_required`
event and SHALL run only if an approver grants approval. If approval is denied,
the node SHALL NOT run, SHALL be marked `blocked`, and its dependents SHALL be
`blocked`. The approval decision SHALL come from outside the model.

#### Scenario: An approved node runs

- **WHEN** a node requires confirmation and the approver grants it
- **THEN** an `approval_required` event SHALL be emitted
- **AND** the node SHALL run and reach `done`

#### Scenario: A denied node does not run and blocks dependents

- **WHEN** a node requires confirmation and the approver denies it
- **THEN** the node SHALL NOT run
- **AND** the node SHALL be `blocked`
- **AND** its dependents SHALL be `blocked`
