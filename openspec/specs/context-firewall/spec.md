# context-firewall Specification

## Purpose

Define the single, fixed pipeline that produces the context entering any session,
including token budgeting, selection policy, and scope distillation.

## Requirements

### Requirement: Context Assembly Pipeline

The context entering any session SHALL be produced by a fixed four-stage
pipeline applied in order: **Selection** (choose which artifacts), **Reference**
(carry them as `artifact://scope/id`, not inline), **Compression** (shrink the
chosen artifacts), and **Budget** (enforce the token ceiling). No session SHALL
receive context that bypasses this pipeline.

#### Scenario: Context is assembled through all four stages in order

- **WHEN** context is assembled for a session
- **THEN** the pipeline SHALL apply Selection, then Reference, then Compression, then Budget
- **AND** the resulting context token count SHALL be within `budget.max_tokens`

### Requirement: Token Budget Enforcement

The Budget stage SHALL enforce `budget.max_tokens` as a hard ceiling. When the
assembled context would exceed the ceiling, the pipeline SHALL truncate so that
the final context is within budget.

#### Scenario: Oversized context is truncated to budget

- **WHEN** the selected and compressed context exceeds `budget.max_tokens`
- **THEN** the pipeline SHALL truncate the context so the final token count is at or below `budget.max_tokens`

#### Scenario: Within-budget context passes unmodified by the Budget stage

- **WHEN** the assembled context is already at or below `budget.max_tokens`
- **THEN** the Budget stage SHALL pass it through without truncation

### Requirement: Context Policy

The Selection stage SHALL be governed by a configurable context policy. The
policy SHALL support `latest` and `tagged` selection. The `relevant` policy is
out of scope for this change.

#### Scenario: Latest policy selects most recent artifacts

- **WHEN** the policy is `latest`
- **THEN** Selection SHALL choose the most recently produced artifacts in scope, in recency order

#### Scenario: Tagged policy selects by tag

- **WHEN** the policy is `tagged` with a given tag
- **THEN** Selection SHALL choose only artifacts whose metadata carries that tag

### Requirement: Scope Distillation

The system SHALL distill a vague request into an explicit scope artifact that
constrains downstream sessions.

#### Scenario: Vague request is distilled into an explicit scope

- **WHEN** scope distillation runs on a free-form request
- **THEN** it SHALL produce a scope artifact stating the explicit objective and boundaries
- **AND** that scope artifact SHALL be referenceable as `artifact://scope/id`
