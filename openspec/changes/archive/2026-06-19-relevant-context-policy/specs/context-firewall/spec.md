## MODIFIED Requirements

### Requirement: Context Policy

The Selection stage SHALL be governed by a configurable context policy. The
policy SHALL support `latest`, `tagged`, and `relevant` selection. The `relevant`
policy SHALL use lexical scoring only; semantic / embedding-based relevance is out
of scope for this change.

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

## ADDED Requirements

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
