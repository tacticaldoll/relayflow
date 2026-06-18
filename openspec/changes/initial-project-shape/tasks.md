## 1. Project Shape

- [x] 1.1 Rename project metadata to RelayFlow in `pyproject.toml` and `openspec/config.yaml` (`project: relayflow`)
- [x] 1.2 Rewrite `README.md` to describe RelayFlow (purpose + link to `docs/vision.md`), replacing starter text
- [x] 1.3 Create `src/relayflow/` package layout with `__init__.py` and module skeletons (`session`, `artifact`, `firewall`, `falsification`, `cli`)
- [x] 1.4 Configure `relayflow` console-script entry point in `pyproject.toml`
- [x] 1.5 Make Definition of Done runnable from module root: test, lint, format commands wired and passing on the empty skeleton

## 2. Artifact System

- [x] 2.1 Define the Artifact type with `type`, `content`, `metadata`, and scope+id identity
- [x] 2.2 Implement SQLite-backed artifact store with write and read-by-(scope,id); not-found signals on missing read
- [x] 2.3 Implement `artifact://scope/id` reference parsing and resolution from the store; fail fast on missing reference
- [x] 2.4 Implement artifact compression (size-threshold → summary), keeping the original artifact retrievable unchanged
- [x] 2.5 Tests: store round-trip, missing-read not-found, reference resolve + fail-fast, compression shrinks tokens and preserves original

## 3. Session Runtime

- [ ] 3.1 Define Session input (`id`, `purpose`, `context`, `constraints`, `budget.max_tokens`) with validation (reject missing budget)
- [ ] 3.2 Define Session output contract (`summary`, `artifacts` as references, `next_actions`)
- [ ] 3.3 Define `LLMClient` interface and a deterministic mock implementation for tests/falsification
- [ ] 3.4 Implement session execution: assemble context (via firewall) → call client → persist + emit output
- [ ] 3.5 Implement persistence (SQLite) of `input`/`output`/artifact references; assert reasoning is NOT stored
- [ ] 3.6 Tests: required-field validation, output contract shape, persistence excludes reasoning

## 4. Context Firewall

- [x] 4.1 Implement the four-stage assembly pipeline as the single context entry point: Selection → Reference → Compression → Budget
- [x] 4.2 Implement context policy: `latest` and `tagged` selection (no `relevant`)
- [x] 4.3 Implement Budget stage: hard `max_tokens` ceiling with truncation; pass-through when already within budget
- [x] 4.4 Implement scope distillation: free-form request → explicit scope artifact (referenceable)
- [x] 4.5 Tests: pipeline order + within-budget result, latest/tagged selection, oversized truncation, distillation produces scope artifact

## 5. Relay Falsification

- [ ] 5.1 Implement relay toggle: relay-off as degenerate config (`N=1`, `budget=∞`, single node) sharing the same code path
- [ ] 5.2 Implement token metering: `peak_session_tokens` across sessions; `single_shot_tokens` from a relay-off unbounded run
- [ ] 5.3 Implement acceptance check producing a `complete` / `not-complete` verdict for a run
- [ ] 5.4 Implement the three-cell experiment matrix runner and result report
- [ ] 5.5 Tests (mock LLM): matrix shows cell-2 fails, cell-3 completes with `peak ≤ B`, and `peak ≤ B < single_shot`

## 6. CLI & Inspect

- [ ] 6.1 Implement `relayflow inspect <session-id>`: read-only trace replay of persisted input/output/artifacts, no model call
- [ ] 6.2 Implement non-zero exit + not-found message for unknown session id
- [ ] 6.3 Wire a CLI entry to run a task (relay on/off) and to run the experiment matrix
- [ ] 6.4 Tests: inspect replays without model call, unknown-id error path

## 7. End-to-End PoC

- [ ] 7.1 Build the V0 demo task (e.g. analyze a large input → Scope → Findings → Report) wired through the relay
- [ ] 7.2 Run the experiment matrix on the demo and confirm `peak_session_tokens ≤ budget < single_shot_tokens` with relay-on completing
- [ ] 7.3 Update `PROJECT.md` if any contract detail drifted during implementation
