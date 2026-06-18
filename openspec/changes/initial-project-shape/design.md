## Context

RelayFlow 從 starter 模板起步，需要第一個可執行骨架來驗證核心賭注：**有界 context
下，靠 Artifact Relay 持續推進大型工作**。本 change 範圍是 V0 — Core PoC，四個能力
（session-runtime / artifact-system / context-firewall / relay-falsification）構成一個
最小閉環，並能自洽證偽。詳見 [docs/vision.md](../../../docs/vision.md)。

約束：V0 不接 worklane / OpenCode / Triggerlane，無外部服務；relay 必須是線性 driver
loop；證偽要能在 mock LLM 下穩定重現。

## Goals / Non-Goals

**Goals:**
- 建立 `relayflow` Python 套件與 CLI（含 `relayflow inspect`），讓 Definition of Done 可執行。
- 實作 Session → Artifact → Session 的線性 relay 閉環，context 全程通過固定四段 pipeline。
- 提供 relay 開關與三格實驗矩陣，輸出 `peak_session_tokens` 與 `single_shot_tokens`。
- 持久化 input/output/artifact（不存推理），並可用 `inspect` 重播 trace。

**Non-Goals:**
- Session Graph / fan-out / 任何 task queue（V0 是 size-1 線性 loop）。
- Artifact 驗收閘門、自主 next-session 生成、`relevant` context policy。
- worklane、Capability Routing、OpenCode、Triggerlane、Memory / Vector / RAG。

## Decisions

- **語言 Python + SQLite**：沿用 starter（pyproject.toml），SQLite 用標準庫 `sqlite3`，
  零外部服務。worklane（Rust）的程序邊界延到 V0→V1，不在本 change。
- **LLM client 抽象 + 可注入 mock**：執行層走一個 `LLMClient` 介面。證偽矩陣與所有單元
  測試用 deterministic mock 驅動，使「relay off+上限失敗 / relay on+上限成功」可重現，
  不依賴真實模型。真實 client 為其中一個實作。
- **Context Assembly Pipeline 為單一進入點**：所有送進 session 的 context 都經
  `assemble(policy, budget) = Selection → Reference → Compression → Budget`。這是
  context-firewall 的本體，也是唯一允許組 context 的路徑（杜絕 inline 旁路）。
- **Relay off = 退化設定，同 code path**：relay off 不另寫路徑，而是 `N=1 session、
  budget=∞、單節點`。對照組因此天然自洽，且 toggle 可當回歸測試。
- **Artifact 一律 by reference (`artifact://scope/id`)**：session 之間只傳引用，
  resolve 發生在 assembly 時。inline 大內容在型別層被禁止。
- **Inspect = trace 重播，非 re-execute**：因為不存推理，無法重現生成；`inspect`
  只讀回持久化的 input/output/artifact，明確不發新 model call。
- **Persistence 不存推理**：store schema 只有 input/output/artifact 欄位，紀律寫進資料模型。

## Risks / Trade-offs

- **壓縮/過濾弄丟下游關鍵細節**（賭注頭號風險）→ V0 用可驗證的笨策略（latest/tagged +
  size-threshold 壓縮），把 `relevant` 隔離為 V1 研究項；compression spec 要求原 artifact
  保留可回溯。
- **Mock 與真實模型行為落差** → 證偽矩陣的「完成/未完成」判定靠 acceptance check 而非
  模型輸出細節；mock 設計成能穩定觸發「上限下塞不下」的失敗，保證矩陣語意成立。
- **Token 計數準確度** → V0 以一致的 tokenizer 量測 `peak_session_tokens` /
  `single_shot_tokens`，重點是兩者相對關係（`peak ≤ B < single_shot`），非絕對精度。
- **過度設計的誘惑** → 任何 graph/queue/worker 概念一律擋在 V0 外；scheduler 是 V1。
