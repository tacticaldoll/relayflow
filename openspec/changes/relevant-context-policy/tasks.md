## 1. Lexical Relevance

- [ ] 1.1 Add a deterministic lexical scorer: count of distinct query terms present in an artifact's content (lowercased, whitespace tokens)
- [ ] 1.2 Add `query` to `ContextPolicy`; implement `relevant` selection (score desc, recency tiebreak, exclude zero, cap by `limit`)
- [ ] 1.3 Validate that `relevant` without a query raises

## 2. Tests

- [ ] 2.1 Higher distinct overlap ranks first
- [ ] 2.2 Ties break by recency
- [ ] 2.3 `limit` caps the selection
- [ ] 2.4 No overlap selects nothing
- [ ] 2.5 Existing `latest`/`tagged` tests still pass; assemble pipeline works with `relevant`

## 3. Definition of Done

- [ ] 3.1 Run full Definition of Done and confirm green
