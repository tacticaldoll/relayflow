## 1. Lexical Relevance

- [x] 1.1 Add a deterministic lexical scorer: count of distinct query terms present in an artifact's content (lowercased, whitespace tokens)
- [x] 1.2 Add `query` to `ContextPolicy`; implement `relevant` selection (score desc, recency tiebreak, exclude zero, cap by `limit`)
- [x] 1.3 Validate that `relevant` without a query raises

## 2. Tests

- [x] 2.1 Higher distinct overlap ranks first
- [x] 2.2 Ties break by recency
- [x] 2.3 `limit` caps the selection
- [x] 2.4 No overlap selects nothing
- [x] 2.5 Existing `latest`/`tagged` tests still pass; assemble pipeline works with `relevant`

## 3. Definition of Done

- [x] 3.1 Run full Definition of Done and confirm green
