## ADDED Requirements

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
