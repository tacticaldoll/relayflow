# RelayFlow

Advance a large task through multiple **context-bounded short sessions** that
pass **artifacts** to one another, with a **Context Firewall** controlling how
much information enters each step.

RelayFlow does not bet that "AI can remember more." It bets that **AI can keep
advancing large work under bounded context, by relaying artifacts**.

The full vision, layered backlog (V0/V1/V2), and the self-falsification metric
live in [docs/vision.md](docs/vision.md). The project contract is in
[PROJECT.md](PROJECT.md).

## Status

V0 — Core PoC. The goal is to prove the core bet, not to ship a framework.
Deliberately out of scope until V2+: Memory, Vector DB / RAG, Multi-Agent,
Knowledge Base, and autonomous task planning.

## Core bet (falsifiable)

A large task can be split into short sessions, each with a bounded context, that
relay artifacts to completion — while no single session ever holds the whole
task's context. RelayFlow proves this by toggling relay **off** (a degenerate
single-session run on the same code path) and comparing the same task under a
bounded budget:

| mode | budget | expected |
| --- | --- | --- |
| relay off | unbounded | completes, large context (measures `single_shot_tokens`) |
| relay off | bounded | fails / truncated |
| relay on | bounded | completes with `peak_session_tokens` within budget |

## Development

This project is spec-driven via OpenSpec. See [AGENTS.md](AGENTS.md) and
[docs/development-flow.md](docs/development-flow.md).

Definition of Done, run from the repo root:

```bash
python -m compileall .
python -m pytest
python -m ruff check .
python -m ruff format --check .
```
