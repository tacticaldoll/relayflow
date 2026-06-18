# artifact-system Specification

## Purpose

Define artifacts — the only thing sessions pass to one another — their type,
SQLite persistence, reference-based addressing, and compression.

## Requirements

### Requirement: Artifact Specification

An Artifact SHALL be a structured session output with the fields `type`,
`content`, and `metadata`. Every stored artifact SHALL be addressable by a stable
identifier within a scope.

#### Scenario: Artifact carries type, content and metadata

- **WHEN** an artifact is created
- **THEN** it SHALL have a `type`, a `content`, and a `metadata` map
- **AND** it SHALL be assigned a stable id within its scope

### Requirement: Artifact Store

Artifacts SHALL be persisted in a SQLite-backed store. The store SHALL support
writing an artifact and reading it back by scope and id.

#### Scenario: Artifact round-trips through the store

- **WHEN** an artifact is written to the store and then read back by its scope and id
- **THEN** the returned artifact SHALL equal the written `type`, `content`, and `metadata`

#### Scenario: Reading a missing artifact

- **WHEN** an artifact is read for a scope/id that was never written
- **THEN** the store SHALL signal not-found rather than returning empty content

### Requirement: Artifact Reference

Sessions SHALL pass artifacts to one another by reference using the
`artifact://scope/id` form. The runtime SHALL NOT inline large artifact content
directly into a session's declared inputs.

#### Scenario: Inputs are expressed as references

- **WHEN** a session declares `inputs` that depend on a prior artifact
- **THEN** each input SHALL be an `artifact://scope/id` reference
- **AND** the referenced content SHALL be resolved from the store at assembly time

#### Scenario: Reference to a missing artifact fails fast

- **WHEN** a session input references an `artifact://scope/id` that does not exist
- **THEN** assembly SHALL fail with a resolution error before the model is called

### Requirement: Artifact Compression

The system SHALL be able to produce a compressed summary of an artifact whose
content exceeds a configured size, reducing token cost while preserving the
detail needed by downstream sessions.

#### Scenario: Large artifact is compressed to a summary

- **WHEN** an artifact larger than the configured threshold is compressed
- **THEN** the produced summary SHALL be smaller in tokens than the original content
- **AND** the original artifact SHALL remain retrievable from the store unchanged
