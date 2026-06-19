# RelayFlow — Vision & Backlog

> 從「Agent Framework」重構為 **Context Firewall + Session Graph + Capability Routing**。
> RelayFlow 不賭「AI 能記住更多」，而賭「AI 能在有界 context 下，透過 Artifact Relay 持續推進大型工作」。

---

## 1. 北極星（North Star）

### 1.1 唯一賭注（可證偽）

> **一個大型任務，可以被切成多個各自 context 有界的短 session，靠彼此傳遞的 artifact 持續推進到完成——而任何單一 session 從未持有整個任務所需的 context。**

### 1.2 頭條指標：relay 開關 = 自洽證偽

任何人都能串 LLM calls。RelayFlow 要證明 **relay 本身有效**，所以需要對照組。
最乾淨的對照不是另寫一個 baseline，而是**把 relay 關掉跑同一套系統**。

關鍵設計：**relay off 不是另一條 code path，而是同一條 pipeline 的退化設定**——
`N=1 session、budget=∞、graph 只有一個節點`。同程式、同模型、同 prompt、同任務，
只差 config。這樣對照組才自洽，不會有兩條路徑各自漂移。

一個開關就能跑出完整的三格實驗矩陣：

| 設定 | budget | 預期 | 證明 |
|---|---|---|---|
| Relay **off**, 無上限 | ∞ | 成功，context 巨大 | 實測 `single_shot_tokens`（非估算） |
| Relay **off**, 同上限 | 例如 4k | **失敗 / 截斷** | 有界的單一 session 做不到 |
| Relay **on**, 同上限 | 例如 4k | **成功** | relay 正是讓它成立的關鍵 |

**通過條件**：第二格失敗、第三格成功，且第三格的
`peak_session_tokens ≤ 預算上限 < single_shot_tokens`，產出可被人工驗收為「完成」。
同一 budget 下差別只有「有沒有 relay」——這就是自洽證偽，是每個 demo 的頭條數字。

### 1.3 明確非目標（這版不做，且不為它們留架構）

- ❌ Memory / 長期記憶
- ❌ Vector DB / RAG（注意：見 §3「相關性是 firewall 自己的核心難題」）
- ❌ Multi-Agent / Agent 人格
- ❌ Knowledge Base
- ❌ 自主任務規劃（next session 由 AI 全自動生成）— V0 走人控/半自動，見 RF-032

全部移到 V2 之後。

---

## 2. 核心概念（canonical terminology）

| 術語 | 定義 | 一句話 |
|---|---|---|
| **Session** | 一次 context 有界的 LLM 工作單元。有 `purpose / context / constraints / budget`，產出 `summary / artifacts / next_actions`。 | 既是工作單元，也是 graph 的節點。 |
| **Artifact** | session 的結構化產出，存於 store，靠 `artifact://scope/id` 引用而非 inline。 | RelayFlow 的靈魂；session 之間只透過 artifact 傳遞。 |
| **Context Firewall** | 決定「哪些資訊、以多大體積」能進入下一個 session 的 context。 | 核心賣點；見 §2.1 pipeline。 |
| **Session Graph** | session 為節點、artifact 為邊的有向圖。 | 差異化；可重播、可視化、可分支。 |
| **Capability** | 一個有 input/output schema 的可呼叫能力（V1 才接）。 | 接世界的方式。 |

### 2.1 Context Assembly Pipeline（這條 pipeline 就是產品本體）

進入任一 session 的 context，必須通過這條固定的四段管線。**Epic 3 的規格本體就是這條管線。**

```
1. Selection   選哪些 artifact 進來      （policy: latest / relevant / tagged）
2. Reference   用 artifact://scope/id 引用，不 inline 大塊原文
3. Compression 把選中的 artifact 縮小   （5000 tokens → 200 tokens summary）
4. Budget      硬上限 + 超過自動截斷    （max_tokens）
```

- **Selection vs Compression 的分工**：Selection 決定「要哪些」，Compression 決定「每個多大」。兩者都減 token，但層次不同，不要混為一卡。
- **`relevant` policy 是整個賭注最硬的地方**（見 §3 風險 1）。V0 先用最笨但可驗證的版本（latest + tagged），`relevant` 標記為高風險研究卡。

---

## 3. 已知風險（驅動排序的根據）

| # | 風險 | 對策（落在哪） |
|---|---|---|
| 1 | **Firewall 的「相關性 + 有損壓縮」就是 RAG 最難的孿生兄弟。** 壓縮/過濾可能弄丟下一個 session 真正需要的細節。 | 列為 V0 頭號風險卡（RF-021/RF-013）。V0 先用可驗證的笨策略，把「relevant」隔離成研究項。 |
| 2 | **Relay 會放大錯誤**：爛 artifact 沿鏈污染下游。 | V1 引入 **Artifact 驗收閘門**（RF-040），V0 至少要能人工拒絕並重生成。 |
| 3 | **Next Session 由誰決定？** AI 全自動 = 規劃難題會漂移；人控 = workflow 工具。 | V0 **人控/半自動**（RF-032）。自主規劃延後到 relay 機制已被證明可靠。 |
| 4 | **Demo 綁死外部 worker** 就讀不懂實驗結果。 | V0 demo 純 relay，**不碰 OpenCode、不碰 Capability**。 |
| 5 | **Replay 語意**：不存推理就無法「重現」（LLM 非決定性）。 | 改名 `inspect`：重播記錄的 I/O trace，不是 re-execute（RF-004）。 |

---

## 4. V0 — Core PoC（只證一件事）

**目標**：完成第一個閉環，並用 §1.2 的指標證明 relay 有效。

```
Long Task → Session → Artifact → Session → Artifact → …  →  完成
                     （全程 peak_session_tokens ≤ 預算）
```

**V0 完全用不到 Epic 4/5/6/7。**

### Epic 1 — Session Runtime

- **RF-001 Session** — `id / purpose / context / constraints / budget`
- **RF-002 Session Output** — `summary / artifacts / next_actions`
- **RF-003 Session Persistence** — 保存 `input / output / artifact`；**不保存完整推理**（紀律約束）
- **RF-004 Session Inspect**（原 Replay）— `relayflow inspect <session-id>`：重播記錄的 I/O trace，明確**不是** re-execute

### Epic 2 — Artifact System（靈魂）

- **RF-010 Artifact Spec** — `type / content / metadata`
- **RF-011 Artifact Store** — SQLite 起步，不上 vector DB
- **RF-012 Artifact Reference** — `inputs: [artifact://scope/123]`，禁止直接塞大量 context
- **RF-013 Artifact Compression** — 5000 → 200 tokens summary。**⚠️ 風險 1**：壓縮必須保留下游需要的關鍵細節，需可驗證

### Epic 3 — Context Firewall（= §2.1 pipeline 的規格本體）

- **RF-020 Context Filter / Selection** — 控制哪些 artifact 能進下一個 session
- **RF-021 Token Budget** — `budget.max_tokens`，超過自動裁切（pipeline 第 4 段）
- **RF-022 Context Policy** — `latest / tagged` 先做；**`relevant` 標記為高風險研究卡，V0 可選**
- **RF-023 Scope Distillation** — 模糊需求 → 明確 scope

### Epic 0 — Falsification Harness（新增，V0 的頭條）

- **RF-090 Relay Toggle** — relay off = pipeline 退化設定（`N=1, budget=∞, 單節點 graph`），同 code path，非另一條路徑
- **RF-091 Token Metering** — 量測並輸出 `peak_session_tokens` 與（relay off 跑出的）`single_shot_tokens`
- **RF-092 Acceptance Check** — 任務產出可被標記為「完成/未完成」
- **RF-093 Experiment Matrix** — 一鍵跑出 §1.2 的三格對照，輸出自洽證偽結果

### V0 Demo（純 relay，零外部 executor）

選一個能讓人**親眼看到 context 維持有界、而工作持續前進**的任務，例如：
「給一份大型文件 / 一個中型 codebase，分階段分析並產出一份結構化報告。」

```
Scope Session      → Scope Artifact
Analysis Session   → Findings Artifact（引用 Scope，不重讀全文）
Synthesis Session  → Report Artifact（引用 Findings，不重讀原文）
```

**最終輸出**：Report + 完整 artifact 鏈 + §1.2 的兩個數字。

### V0 Exit Criteria

- [ ] 至少 3 段 session 的閉環跑通
- [ ] §1.2 三格矩陣成立：relay off+上限 **失敗**、relay on+上限 **成功**
- [ ] `peak_session_tokens ≤ 預算上限 < single_shot_tokens`（後者為 relay off 實測）
- [ ] 產出被人工驗收為「完成」
- [ ] `relayflow inspect` 能重播整條鏈

---

## 5. V1 — 差異化 + 接執行層

**前提**：V0 已證明 relay 機制可靠。V1 才開始驗證「relay 能驅動真實 worker」。

### 執行基底：worklane（已延後 — 2026-06-19 決定）

原規劃把 [worklane](https://github.com/tacticaldoll/worklane)（Rust typed background
job runner）當執行基底。實際讀過 worklane 原始碼後**推翻了原本的整合假設**：

> worklane 的 CLI `wl` 是 **operator-only**（只有 `dead-letters list|requeue|purge`
> 與 `stats`）——**沒有 `wl enqueue/reserve/ack`**。enqueue/reserve/ack 全是 async
> Rust trait method，且 worklane 無 server/daemon/socket。它是要被 **Rust service
> embed** 的 library。所以「Python shell `wl` 當 broker」這條路不存在。

真實整合只能寫 Rust：一個 embed worklane 的 host（handler shell `relayflow run-node`，
並自造一個 enqueue 入口，因為 worklane 沒有外部 enqueue 通道）。範圍遠大於原想。

**決定：延後 worklane。** 理由：

- 它獨有、而我們還沒有的只有「跨程序/跨機器分散」與「Postgres/Redis 後端」——
  RelayFlow 現階段命題用不到。
- durability / retry-as-jobs / parked approval 已由
  [`durable-scheduler`](../openspec/specs/durable-scheduler/spec.md)（純 Python +
  SQLite，change `durable-graph-scheduler`）交付。
- 花一個 Rust 橋接服務去拿「還用不到的東西」＝提前上基底，違反一路的紀律。

**重啟條件**：真的需要把 worker 分散到多程序/多機器時再回來，且屆時走 Rust 橋接 host
（或整體改 Rust）有真實需求撐腰。屆時 [`Broker` 契約](../src/relayflow/broker.py)
已就位——換的是後端實作，不是上層語義。

**保留的設計不變式**（未來任何 broker 後端都適用）：

> 執行基底只負責派發 / 重試 / lease / 並發；「有哪些工作、做完沒、artifact 是否驗收」
> 永遠由 **Session Graph + Artifact** 持有。job 是薄信封（只帶 `node_id`），狀態 ephemeral，
> 不得編碼業務真相。冪等靠 CAS-claim + 真相在 artifact。

### Epic 4 — Session Graph（差異化）

- **RF-030 Graph Node** — session 即節點
- **RF-031 Graph Edge** — artifact 即邊
- **RF-032 Next Session Generator** — **V0/V1 人控或半自動建議**；自主生成是 V2 議題（風險 3）
- **RF-033 Graph Visualizer** — 先輸出可讀格式即可
- **RF-034 Artifact Acceptance Gate**（新增，風險 2）— artifact 可被驗收/拒絕；拒絕 → 觸發重生成，避免 relay 放大錯誤
- **RF-035 Session Graph Scheduler**（新增）— node 在「input artifact 到齊且驗收」時才 ready；ready set 是 graph 狀態的**投影**，非獨立 store。執行由 worklane 承載（lane/concurrency/retry），真相仍在 graph+artifact

### Epic 5 — OpenCode Integration（第一個真實 Worker）

- **RF-050 OpenCode Executor** — `opencode run`，透過 worklane job 派發（async dispatch + lease + timeout）
- **RF-051 Patch Artifact** — `patch / summary`
- **RF-052 Test Artifact** — `tests / status`（這也是程式類 artifact 的驗收訊號）
- **RF-053 File Scope** — `allowed_paths`，避免污染整個 repo

### Epic 6 — Triggerlane Bridge（與執行層解耦）

- **RF-060 Event Emit** — `event: { type, payload }`
- **RF-061 Event Listener** — 接收 Triggerlane 回報
- **RF-062 Human Approval** — `requires_confirmation`；park 中的 session 用 worklane scheduled/delayed enqueue 實作 timeout 與 resume

> **依賴風險**：OpenCode / Triggerlane 是外部/兄弟專案。Bridge 只定義介面（emit/listen），**V1 不讓核心依賴它們已就緒**。

### V1 Demo（原「第一個 Demo」，現在站在 V0 的地基上）

User：「幫我實作 OpenAPI Loader」

```
Scope Session          → Scope Artifact
Capability Session*    → Capability Artifact   (*若 Capability 仍在 V2，可由人提供)
Implementation Session → OpenCode → Patch Artifact + Test Artifact
Summary Session        → Summary Artifact
```

**輸出**：Session Graph + Patch + Tests + Artifacts。

---

## 6. V2 — 接世界 + 規模化

### Epic 7 — Capability Routing

- **RF-070 Capability Schema** — `id / description / input_schema / output_schema`
- **RF-071 Registry** — Capability Registry
- **RF-072 OpenAPI Import** — `openapi.json` → capabilities
- **RF-073 Capability Discovery** — 根據 scope 找出適合能力

> Capability Routing 本質是獨立的 tool-discovery / MCP-like 層，與 context-relay 命題正交。獨立成 V2，避免散焦。

### 其後

- Memory / 長期記憶
- Vector DB / RAG（含 firewall 的 `relevant` policy 的成熟版）
- Multi-Agent
- Knowledge Base
- 自主 Next Session 規劃（RF-032 的全自動版）

---

## 7. 與原始 backlog 的主要差異（變更摘要）

| 變更 | 原始 | 修正後 | 理由 |
|---|---|---|---|
| 新增頭條指標 | 無 | Epic 0 + §1.2 | demo 需對照組才能證明 relay 有效 |
| Demo 去耦 | 第一個 demo 用 OpenCode + Capability | V0 demo 純 relay | 讀得懂實驗結果，不混淆「賭注錯」與「整合壞」 |
| Capability 降級 | Epic 5（V0 內） | Epic 7（V2） | 與核心命題正交，第二個產品 |
| OpenCode 降級 | Epic 6（V0 內） | Epic 5（V1） | 驗證「接執行」是 V1 命題 |
| Next Session 定位 | 未定 | V0/V1 人控（RF-032） | 避免賭自主規劃 |
| Replay → Inspect | `replay` | `inspect`（重播 trace） | 不存推理 ⇒ 無法 re-execute |
| 新增驗收閘門 | 無 | RF-034 | 防止 relay 放大錯誤 |
| Firewall 風險前置 | RF-013/020 中段卡 | §3 頭號風險 | 它就是賭注成敗所在 |
