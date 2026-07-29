# M2 检索与问答 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打通混合检索 `POST /search` 与流式问答 `POST /chat/completions`（SSE），含会话/引用落库与前端问答页。

**Architecture:** `retrieval` 负责双路召回 + RRF + expand；`chat` 负责会话、提示词、SSE、引用校验。查询侧复用 `normalize` / `build_tsv`。模型用 Fake。KB 可见性 = 租户内未删除库。

**Tech Stack:** FastAPI、SQLAlchemy async、pgvector、jieba、Celery 无关、React + TanStack Query + 现有 `sse.ts`。

## Global Constraints

- 规格：`docs/superpowers/specs/2026-07-29-m2-retrieval-chat-design.md`
- RRF `k=60`；expand 默认 1；rerank 默认关；拒答：空召回或 top1 RRF &lt; 0.35
- Fake Embedding + Fake LLM；跨模块只调 service
- 租户上下文仅来自 JWT；RLS 与 M1 同模式
- Conventional commits；分支 `feat/m2-retrieval`

---

### Task 1: 迁移与 Chat ORM

**Files:**
- Create: `backend/alembic/versions/20260729_0003_chat_conversations.py`
- Create: `backend/app/modules/chat/__init__.py`
- Create: `backend/app/modules/chat/models.py`
- Modify: `backend/alembic/env.py`（import chat models）

**Interfaces:**
- Produces: ORM `Conversation`, `Message`, `Citation`；表 `conversations`/`messages`/`citations` + RLS

- [ ] **Step 1:** 按 `docs/02` §4.7 写 Alembic `0003`（UUID PK、kb_ids 数组、message status check、citations UNIQUE、RLS + DEFAULT PRIVILEGES 已由 0001 覆盖）
- [ ] **Step 2:** 写 `chat/models.py` 映射上述表；`Message.status` 取值 `streaming|completed|failed`
- [ ] **Step 3:** `alembic/env.py` 增加 `from app.modules.chat import models as chat_models  # noqa: F401`
- [ ] **Step 4:** Run: `cd backend && uv run alembic upgrade head` — Expected: upgrade to `0003_chat`
- [ ] **Step 5:** Commit `feat(m2): 会话/消息/引用表与 ORM`

---

### Task 2: RRF 与引用校验纯函数

**Files:**
- Create: `backend/app/modules/retrieval/rrf.py`
- Create: `backend/app/modules/chat/citations.py`
- Create: `backend/tests/test_rrf.py`
- Create: `backend/tests/test_citation_validate.py`

**Interfaces:**
- Produces:
  - `rrf_fuse(ranked_lists: list[list[str]], *, k: int = 60) -> list[tuple[str, float]]`（id → score，降序）
  - `validate_citations(text: str, max_index: int) -> tuple[str, list[int]]`（清洗后正文，实际用到的 1-based index 列表）

- [ ] **Step 1:** 写失败测试：两路排序 RRF 合并；正文含 `[1][99]` 时剔除 99
- [ ] **Step 2:** Run `pytest tests/test_rrf.py tests/test_citation_validate.py -v` — FAIL
- [ ] **Step 3:** 实现 `rrf.py` / `citations.py`
- [ ] **Step 4:** pytest PASS
- [ ] **Step 5:** Commit `feat(m2): RRF 融合与引用编号校验`

---

### Task 3: Retrieval 模块 + POST /search

**Files:**
- Create: `backend/app/modules/retrieval/{__init__,base,vector,fulltext,expand,service,repository,schemas,router}.py`
- Modify: `backend/app/api.py` — include retrieval router
- Create: `backend/tests/test_search_api.py`

**Interfaces:**
- Consumes: `Chunk`/`Document`/`KnowledgeBase`；`normalize`；`build_tsv`；`EmbeddingDep`
- Produces: `RetrievalService.search(tenant_id, query, kb_ids, top_k, options) -> SearchResponse`
- Router: `POST /api/v1/search`

- [ ] **Step 1:** 实现 repository：按 kb_ids 向量 Top-N、全文 Top-N；expand 拉同文档 seq±n
- [ ] **Step 2:** `RetrievalService`：embed query → 并行双路 → RRF → expand → 组装 `SearchHit`
- [ ] **Step 3:** schemas + router；`kb_ids` 空则取租户全部未删 KB
- [ ] **Step 4:** 集成测：造 KB+假 chunk（或依赖 fixture 最小插入）后 `/search` 200 且含 `scores.rrf`
- [ ] **Step 5:** Commit `feat(m2): 混合检索与 POST /search`

---

### Task 4: Chat 服务 + SSE completions

**Files:**
- Create: `backend/app/modules/chat/{repository,schemas,prompts,refuse,sse,service,router}.py`
- Modify: `backend/app/api.py` — include chat router
- Create: `backend/tests/test_chat_sse.py`

**Interfaces:**
- Consumes: `RetrievalService.search`；`LLMDep.stream`
- Produces: SSE 事件序 `message_created` → `retrieval` → (`citations` → `delta`* → `done`) | `no_answer`
- Routes: conversations CRUD + `POST /chat/completions`

- [ ] **Step 1:** prompts：系统提示 + 证据块 `[i] title/path/page\ncontent`
- [ ] **Step 2:** refuse：hits 空或 top rrf &lt; threshold → no_answer
- [ ] **Step 3:** service 编排落库 + StreamingResponse；断开时 status=failed
- [ ] **Step 4:** SSE 冒烟测：Fake 下收到 `done` 或 `no_answer`
- [ ] **Step 5:** Commit `feat(m2): 流式问答与会话 API`

---

### Task 5: 前端问答页

**Files:**
- Create: `frontend/src/features/chat/{api.ts,hooks.ts,ChatPage.tsx,EvidencePanel.tsx}`
- Modify: `frontend/src/app/routes.tsx` — ChatPage
- Modify: `frontend/src/app/placeholders.tsx` — 去掉 Chat 占位或改 milestone

**Interfaces:**
- Consumes: `streamEvents('/chat/completions', body)`；knowledge list API
- Produces: 可发问、流式渲染、证据面板

- [ ] **Step 1:** api/hooks：list KB、create conversation、stream completions
- [ ] **Step 2:** ChatPage：消息列表 + 输入框；解析 SSE 更新 UI
- [ ] **Step 3:** EvidencePanel 展示 citations
- [ ] **Step 4:** `pnpm lint && pnpm typecheck`
- [ ] **Step 5:** Commit `feat(m2): 前端问答与证据面板`

---

### Task 6: 进展文档与手工冒烟

**Files:**
- Modify: `docs/07-progress.md`

- [ ] **Step 1:** 本地：`make migrate`；对已有 ready 文档 `/search` + `/chat` 冒烟
- [ ] **Step 2:** 更新 07-progress M2 状态
- [ ] **Step 3:** Commit `docs: 记录 M2 进展`

---

## Spec coverage

| 规格项 | Task |
| --- | --- |
| 0003 会话表 | 1 |
| RRF / 引用校验 | 2 |
| 混合检索 + /search | 3 |
| SSE 问答 + 拒答 | 4 |
| 前端 | 5 |
| Fake / 租户 KB | 3–4 |
| 非目标（grants/pdf.js/feedback） | 不实现 |

## Placeholder scan

无 TBD；expand/rerank/threshold 均有默认值。
