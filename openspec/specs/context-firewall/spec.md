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
policy SHALL support `latest`, `tagged`, and `relevant` selection. The `relevant`
policy SHALL use lexical scoring only; semantic / embedding-based relevance is out
of scope.

#### Scenario: Latest policy selects most recent artifacts

- **WHEN** the policy is `latest`
- **THEN** Selection SHALL choose the most recently produced artifacts in scope, in recency order

#### Scenario: Tagged policy selects by tag

- **WHEN** the policy is `tagged` with a given tag
- **THEN** Selection SHALL choose only artifacts whose metadata carries that tag

#### Scenario: Relevant policy selects by lexical overlap with a query

- **WHEN** the policy is `relevant` with a query
- **THEN** Selection SHALL choose artifacts whose content shares terms with the query, most-relevant first
- **AND** artifacts with no term overlap SHALL be excluded

### Requirement: Lexical Relevance Selection

The `relevant` policy SHALL score each candidate artifact by the number of
distinct query terms present in its content, rank by score descending with
recency as the tiebreak, exclude zero-score artifacts, and cap the result at the
policy's `limit` when set. Scoring SHALL be deterministic and SHALL NOT use
embeddings or any external service.

#### Scenario: Higher term overlap ranks first

- **WHEN** two artifacts both overlap the query but one shares more distinct query terms
- **THEN** the artifact with more distinct overlapping terms SHALL rank first

#### Scenario: Ties break by recency

- **WHEN** two artifacts have equal term overlap with the query
- **THEN** the more recently produced artifact SHALL rank first

#### Scenario: Limit caps the selection

- **WHEN** the policy sets a `limit` of N and more than N artifacts overlap the query
- **THEN** Selection SHALL return at most N artifacts

#### Scenario: A query with no overlap selects nothing

- **WHEN** no artifact in scope shares any term with the query
- **THEN** Selection SHALL return an empty result

### Requirement: Scope Distillation

The system SHALL distill a vague request into an explicit scope artifact that
constrains downstream sessions.

#### Scenario: Vague request is distilled into an explicit scope

- **WHEN** scope distillation runs on a free-form request
- **THEN** it SHALL produce a scope artifact stating the explicit objective and boundaries
- **AND** that scope artifact SHALL be referenceable as `artifact://scope/id`
