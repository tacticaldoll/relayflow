## Context

The Context Firewall's Selection stage supports `latest`/`tagged`. `relevant` was
deferred in V0 as the high-risk relevance judgment. This adds a lexical, pure-
Python `relevant` policy — the simplest verifiable relevance — without embeddings.

## Goals / Non-Goals

**Goals:**
- A `relevant` policy: deterministic lexical term-overlap scoring against a query.
- Rank by distinct-overlap desc, recency tiebreak; exclude zero overlap; cap by limit.

**Non-Goals:**
- Embeddings, vector DB, semantic similarity, learned ranking, query expansion (V2).
- Changing `latest` / `tagged` behavior.

## Decisions

- **Lexical, not semantic.** Score = count of distinct query terms appearing in the
  artifact content. Chosen because it is deterministic, dependency-free, and
  testable; it proves the firewall can do relevance selection without committing to
  the embeddings substrate. Documented in the spec so it is not mistaken for RAG.
- **Query lives on the policy** (`ContextPolicy.query`), not inferred from the
  session, so selection is explicit and unit-testable in isolation.
- **Recency tiebreak reuses the store's order.** `store.latest(scope)` already
  returns recency-desc; scoring is a stable sort over that list, so equal scores
  keep recency order for free.
- **Zero-overlap excluded.** "Relevant" means shares ≥1 term; non-overlapping
  artifacts are dropped rather than ranked last, matching the intent of the policy.

## Risks / Trade-offs

- **Lexical overlap is shallow** (misses synonyms/paraphrase) → acceptable for V1;
  it is explicitly the floor, with semantic relevance as the V2 upgrade. The spec
  names it lexical so expectations are correct.
- **Tokenization choice affects matching** → reuse the existing whitespace
  tokenizer (lowercased) for consistency with token budgeting; punctuation-tight
  matching is good enough for the deterministic V1 contract.
