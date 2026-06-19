## MODIFIED Requirements

### Requirement: Graph Visualizer

The system SHALL render a graph as readable text showing each node with its status
and its kind (`session` or `execution`), and each dependency edge annotated with
the artifact reference it carries.

#### Scenario: Visualize renders nodes, statuses and edges

- **WHEN** a graph is visualized
- **THEN** the output SHALL list each node with its status
- **AND** it SHALL show the dependency edges between nodes

#### Scenario: Visualize shows node kind and edge artifact

- **WHEN** a graph with session and execution nodes is visualized
- **THEN** each node SHALL show its kind (`session` or `execution`)
- **AND** each edge SHALL show the artifact reference carried from producer to consumer
