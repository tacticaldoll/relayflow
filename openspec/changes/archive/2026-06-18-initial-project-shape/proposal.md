## Why

RelayFlow 的核心賭注是「AI 能在有界 context 下，透過 Artifact Relay 持續推進大型工作」。
這份 change 建立 V0 — Core PoC 的最小骨架，並讓賭注**可被自洽證偽**：用同一套系統把
relay 開關關掉跑同一任務，比較有界 budget 下「有 relay / 無 relay」的結果差異。

repo 目前仍是 starter 模板（[PROJECT.md](../../../PROJECT.md) 為 placeholder、尚無真實
套件），Definition of Done 還不具意義。本 change 負責把它變成可執行的專案骨架。

## What Changes

- 替換 placeholder 專案 metadata（`PROJECT.md`、`README.md`、`pyproject.toml`、
  `openspec/config.yaml` 的 `project` 名稱）為 RelayFlow。
- 選定 **Python** 套件 / CLI 佈局，提供 `relayflow` 指令，含 `relayflow inspect
  <session-id>` 入口；讓 build / test / lint / format 成為可從模組根執行的 Definition of Done。
- 新增 **Session Runtime**：context 有界的 session 工作單元，含輸出契約、持久化
  （存 input/output/artifact，不存完整推理）、與 `inspect`（重播 I/O trace，非 re-execute）。
- 新增 **Artifact System**：artifact spec、SQLite store、`artifact://scope/id` 引用
  （禁止 inline 大量 context）、artifact 壓縮。
- 新增 **Context Firewall**：固定的 Context Assembly Pipeline
  （Selection → Reference → Compression → Budget），含 token budget 硬上限與裁切、
  context policy（先做 `latest` / `tagged`）、scope distillation。
- 新增 **Relay Falsification**：relay toggle（off = 退化設定 `N=1, budget=∞, 單節點`，
  同 code path）、token metering、三格實驗矩陣、acceptance check。

**範圍限制（不在本 change）**：worklane、Session Graph、Artifact 驗收閘門、Capability
Routing、OpenCode、Triggerlane、Memory / Vector / RAG / Multi-Agent。皆為 V1/V2，見
[docs/vision.md](../../../docs/vision.md)。`relevant` context policy 為高風險研究項，
本 change 只實作 `latest` / `tagged`。

## Capabilities

### New Capabilities
- `session-runtime`: context 有界的 session 工作單元——id/purpose/context/constraints/budget
  輸入，summary/artifacts/next_actions 輸出，持久化（不含推理），以及 `inspect` trace 重播。
- `artifact-system`: artifact 的型別化規格、SQLite 儲存、`artifact://scope/id` 引用語意、
  與壓縮（大內容 → 摘要）。
- `context-firewall`: 進入任一 session 的 context 必須通過的四段 assembly pipeline，
  含 token budget 硬上限、context policy、scope distillation。
- `relay-falsification`: relay 開關（含退化設定）、token 量測、三格對照矩陣與
  任務完成驗收，用以自洽證偽核心賭注。

### Modified Capabilities
<!-- 無既有 spec；openspec/specs/ 為空。 -->

## Impact

- **新套件佈局**：建立 `relayflow` Python 套件與 `relayflow` CLI（含 `inspect`）。
- **依賴**：Python + SQLite（標準庫 `sqlite3`），LLM client（介面抽象，可注入 mock 以利測試）。
- **檔案**：改寫 `PROJECT.md`/`README.md`/`pyproject.toml`/`openspec/config.yaml`；
  新增 `src/` 套件、tests、Definition of Done 指令。
- **無外部服務依賴**（V0 不接 worklane / OpenCode / Triggerlane）。
- **可測試性**：證偽矩陣需可在 mock LLM 下穩定跑出「relay off+上限失敗 / relay on+上限成功」。
