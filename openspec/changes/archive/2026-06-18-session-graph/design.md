## Context

V0 delivered a linear relay (`falsification.run_task` loops over a list of
`SessionInput`). V1's differentiation is the **Session Graph**: a DAG of sessions
connected by artifact dependencies, advanced by a scheduler, guarded by an
acceptance gate. This change builds that substrate in pure Python, composing the
existing `session.run_session` and the artifact store. No worklane, no async, no
external executor — the language/boundary decision stays deferred.

## Goals / Non-Goals

**Goals:**
- A graph of nodes (sessions) and edges (artifact dependencies) with derived node
  status.
- A synchronous readiness scheduler whose ready set is a projection of graph +
  artifact state.
- An acceptance gate that stops bad artifacts propagating, with bounded
  regeneration.
- Human-controlled node/edge construction and a text visualizer.

**Non-Goals:**
- worklane / async / concurrent dispatch / retries-as-jobs (a later change).
- OpenCode executor, Triggerlane bridge.
- Autonomous (model-driven) next-session generation.
- Persisting the ready set or any scheduler state as an independent store.

## Decisions

- **Ready = inputs present AND accepted; derived every tick.** The scheduler
  recomputes the ready set from node statuses and artifact acceptance on each
  tick. There is no separate queue — graph + artifact store remain the single
  source of truth. This is the principle that later lets worklane be only a
  dispatch layer without owning truth.
- **Dependencies are the session input's `inputs` refs.** A node depends on the
  artifact references its `SessionContext.inputs` declares. Edges are derived from
  those refs (producer node = the node whose `{id}.out` matches the ref). Nodes
  using a policy instead of explicit inputs have no inbound edges (roots).
- **Acceptance gate is a pluggable predicate** `accept(artifact) -> bool`, default
  accept-all. On reject, the node re-runs up to `max_attempts`; if still rejected,
  the node is `failed` and dependents become `blocked`. Acceptance state is
  tracked per artifact reference in the graph run, keyed off the store.
- **Compose, do not refactor V0.** `graph.py` is new and calls `run_session`
  directly. `falsification.run_task` stays as the linear runner; the graph is the
  general case. A future change may express `run_task` in terms of the graph.
- **Synchronous topological execution.** The scheduler loops: compute ready set,
  run each ready node once (with acceptance + regeneration), repeat until no node
  is ready. Termination: every tick either advances a node to `done`/`failed` or
  the run is stuck (remaining nodes all blocked) and stops.

## Risks / Trade-offs

- **Deterministic regeneration cannot fix a rejected artifact** (mock re-runs
  produce the same output) → bounded `max_attempts` then `failed`; tests use an
  acceptor that accepts after N attempts to exercise the regenerate path.
- **Cycle or unsatisfiable dependency would not terminate** → the scheduler stops
  when no node is ready; remaining non-`done` nodes are reported `blocked`, so a
  bad graph fails loudly rather than looping.
- **Edge inference from refs is convention-bound** (`{node_id}.out`) → kept
  explicit and documented; callers declare refs, the graph maps them to producers.
- **Scope creep toward a scheduler framework** → V1 stays synchronous and
  single-process; concurrency/retry semantics are explicitly a worklane change.
