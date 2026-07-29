# 真实 Provider 与召回对比 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 拆分 LLM/Embedding/Rerank 配置，接入 DeepSeek + DashScope，默认真实重排，并提供 Fake/Real 召回对比脚本。

**Architecture:** Settings 三套凭证；factory 分别构造 Client；RetrievalService 在 RRF 后可选调用 RerankProvider；对比脚本调 HTTP `/search` 落报告。

**Tech Stack:** FastAPI、httpx、现有 openai_compatible Provider、Celery reingest。

## Global Constraints

- 规格：`docs/superpowers/specs/2026-07-29-real-providers-compare-design.md`
- 向量维 1024；Embedding 批 ≤10；Rerank 路径 `/reranks`
- API Key 只进本地 `.env`，禁止 commit
- Fake 环境默认不调外网 rerank
- Conventional commits；分支 `feat/real-providers-compare`

---

### Task 1: Settings + openai_compatible + factory

**Files:**
- Modify: `backend/app/platform/config.py`
- Modify: `backend/app/platform/llm/openai_compatible.py`
- Modify: `backend/app/platform/llm/factory.py`
- Modify: `backend/.env.example`
- Modify: `backend/tests/test_providers.py`

- [ ] **Step 1:** 增加 embedding/rerank 独立 URL/Key/model/batch；`retrieval_rerank_default` optional
- [ ] **Step 2:** Embedding POST 带 `dimensions`；Rerank 用 `/reranks`
- [ ] **Step 3:** factory 三 Client；close 全关；rerank 跟 `rerank_provider` 而非 llm
- [ ] **Step 4:** 单测 mock 通过；Commit `feat(providers): 拆分 Embedding/Rerank 配置与 DashScope 兼容`

---

### Task 2: Retrieval 接线 Rerank

**Files:**
- Modify: `backend/app/platform/deps.py`
- Modify: `backend/app/modules/retrieval/service.py`
- Modify: `backend/app/modules/retrieval/router.py`
- Modify: `backend/app/modules/chat/service.py`（SearchOptions 传默认）
- Modify: ingestion embed batch（若硬编码 64）

- [ ] **Step 1:** `RerankDep`；service 在 opts.rerank 时重排 Top 候选
- [ ] **Step 2:** router/chat 默认：settings 决定；Fake 测保持 false
- [ ] **Step 3:** pytest search 仍绿；Commit `feat(retrieval): 接线 Cross-Encoder 重排`

---

### Task 3: 对比脚本 + 本地联调文档

**Files:**
- Create: `backend/scripts/compare_retrieval.py`
- Modify: `docs/07-progress.md`
- Local only: `backend/.env`

- [ ] **Step 1:** 脚本：登录 → 多 query search → JSON/MD 报告
- [ ] **Step 2:** 写 `.env`、重启、reingest、跑对比与聊天冒烟
- [ ] **Step 3:** 更新 07-progress；Commit `feat(tooling): 召回对比脚本与真实模型联调记录`
