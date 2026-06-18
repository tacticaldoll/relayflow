## Why

V0 proved the relay bet on a **linear** chain. RelayFlow's differentiation is the
**Session Graph**: sessions as nodes, artifacts as edges, with a scheduler that
advances work as dependencies become ready — and an **acceptance gate** so a bad
artifact cannot propagate and amplify down the chain.

This change builds the graph substrate in pure Python. It deliberately does
**not** introduce worklane, async execution, OpenCode, or Triggerlane: the
scheduler stays synchronous and single-process so the graph mechanics and the
error-amplification guard can be proven before any execution-substrate or
language/boundary decision is made (see [docs/vision.md](../../../docs/vision.md)).

## What Changes

- Add a **Session Graph**: nodes wrap session inputs; edges are artifact
  dependencies between nodes; node status is derived (pending/ready/running/
  done/blocked/failed).
- Add an **Artifact Acceptance Gate**: a produced artifact is accepted or
  rejected by a pluggable acceptor; a rejected artifact triggers re-generation of
  its node up to a bounded number of attempts; dependents stay blocked until
  their inputs are accepted.
- Add a **synchronous Scheduler**: a node is ready when all its input artifacts
  exist and are accepted. The ready set is computed as a **projection of graph +
  artifact state**, not stored separately. The scheduler runs ready nodes until
  none remain ready.
- Add **human-controlled next sessions**: nodes and edges are added explicitly by
  the caller. No model-driven autonomous planning in V1.
- Add a **text Graph Visualizer**: render nodes, edges, and statuses readably.
- Extend the CLI with a command to run a demo graph and visualize it.

**Out of scope (later V1/V2 changes)**: worklane execution substrate, async/
concurrent dispatch, retries-as-jobs, OpenCode executor, Triggerlane bridge,
autonomous next-session generation, the `relevant` context policy.

## Capabilities

### New Capabilities
- `session-graph`: nodes (sessions), edges (artifact dependencies), the artifact
  acceptance gate, the synchronous readiness scheduler, human-controlled next
  sessions, and a text visualizer.

### Modified Capabilities
<!-- None. session-runtime, artifact-system, and context-firewall are reused
     unchanged; the graph composes run_session and the artifact store. -->

## Impact

- **New module** `src/relayflow/graph.py` composing `session.run_session` and the
  artifact store; no changes to V0 behavior.
- **New demo graph** reusing the existing marker task decomposition as a DAG.
- **CLI**: add a `graph` subcommand (run + visualize).
- **No new dependencies**; still pure Python + SQLite, no external services.
