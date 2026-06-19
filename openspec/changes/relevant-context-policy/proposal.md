## Why

V0 shipped the Context Firewall with `latest` and `tagged` selection and
deliberately deferred `relevant` as the hardest, riskiest part — relevance
selection is the lossy "what does the next session actually need" judgment that
is RAG's twin. This change adds a **lexical** `relevant` policy: deterministic
term-overlap scoring against a query, **no embeddings and no vector DB**. Semantic
relevance stays V2.

This backfills the V0 firewall gap with the simplest verifiable form of
relevance, keeping the heavy substrate (embeddings) deferred until it is needed.

## What Changes

- `ContextPolicy` gains a `relevant` kind with a `query`. Selection scores each
  artifact in scope by **lexical term overlap** with the query, returns the
  top-`limit` by score (recency as tiebreak), and excludes zero-overlap artifacts.
- Relevance scoring is deterministic and dependency-free (token-set overlap),
  explicitly **not** semantic — documented so it is not mistaken for RAG.

**Out of scope (V2)**: embeddings, vector DB, semantic similarity, learned
ranking, query expansion.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `context-firewall`: the **Context Policy** requirement adds `relevant`
  selection; a new **Lexical Relevance Selection** requirement pins the scoring
  contract (lexical, deterministic, no embeddings).

## Impact

- `src/relayflow/firewall.py`: `ContextPolicy` gains `query`; `select` handles
  `relevant`; a small lexical scorer is added.
- No new dependencies; pure Python. Existing `latest`/`tagged` behavior unchanged.
