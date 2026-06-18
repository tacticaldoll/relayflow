# Project Contract

Fill this file in during the first project-specific OpenSpec change. Keep it
short and concrete; it is the orientation layer for humans and AI agents.

## Purpose

RelayFlow 把大型任務拆成多個 **context 有界的短 session**，session 之間只透過
**artifact** 傳遞，由 **Context Firewall** 控制每一步進入 context 的資訊量。

它賭的不是「AI 能記住更多」，而是「AI 能在有界 context 下，透過 Artifact Relay
持續推進大型工作」。完整的願景、分層 backlog 與證偽指標見
[docs/vision.md](docs/vision.md)。

刻意不做（移到 V2 之後）：Memory、Vector DB / RAG、Multi-Agent、Knowledge Base、
自主任務規劃。

## Core Contract

**Artifact Relay 的完整性**必須最先被保護：

- session 之間只透過 `artifact://scope/id` 引用傳遞，**不得 inline 大量 context**。
- 每個 session 的 context 必須通過固定的 Assembly Pipeline
  （Selection → Reference → Compression → Budget），且不得超過 `budget.max_tokens`。
- persistence 保存 `input / output / artifact`，**不保存完整推理**。
- 可證偽的頭條指標：`peak_session_tokens ≤ 預算上限 < single_shot_tokens`，
  且任務產出可被人工驗收為「完成」。

## Terminology

優先使用以下 canonical 術語（同義詞請收斂）：

- **Session** — 一次 context 有界的 LLM 工作單元，也是 Session Graph 的節點。
- **Artifact** — session 的結構化產出，以 `artifact://scope/id` 引用，不 inline。
- **Context Firewall** — 決定哪些 artifact、以多大體積進入下一個 session 的機制。
- **Session Graph** — session 為節點、artifact 為邊的有向圖。
- **Capability** — 有 input/output schema 的可呼叫能力（V1 才接）。
- **Inspect**（非 Replay）— 重播記錄的 I/O trace，**不是** re-execute。

## First Project Change

第一個 OpenSpec change 命名為 `initial-project-shape`，範圍鎖定
[docs/vision.md](docs/vision.md) 的 **V0 — Core PoC**，不得提前納入 V1/V2 內容。

該 change 應：

- 替換 placeholder 專案 metadata
- 定義 V0 的第一批 specs：Session Runtime（Epic 1）、Artifact System（Epic 2）、
  Context Firewall（Epic 3）、Falsification Harness（Epic 0）
- 選定套件 / 指令 / 模組佈局，並提供 `relayflow inspect <session-id>` 入口
- 讓 Definition of Done 可從模組根目錄執行

在第一個真實套件存在前，build / test / vet / format 還不是有意義的 Definition of
Done；第一個專案 change 負責讓它們變得有意義。

## Change Prioritization

When comparing possible changes, prefer the one that protects the core contract
earliest:

1. Correctness, data integrity, lifecycle safety, and security foundations.
2. Specified feature completeness for concepts already declared in OpenSpec.
3. Operator and developer ergonomics.
4. Scale-out, integrations, and optional platform features.

Do not add scale-out or integration scope merely because a correctness change
enables it. Keep enabling contract changes separate and small.
