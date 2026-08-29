# M6 验收修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or implement task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 前端按 `my_permission` 门控写操作；PATCH settings 浅合并且只提交脏键。

**Architecture:** `resolve_kb_permission` 与 `visible_kb_ids` 同源；`_kb_out` 注入 `my_permission`；`shallow_merge_settings` 改写入语义；前端 `canWrite` 与 dirty payload。

**Tech Stack:** FastAPI + pytest；React + TanStack Query；`make openapi`

**Spec:** `docs/superpowers/specs/2026-08-29-m6-permission-settings-fix-design.md`

## Global Constraints

- `canWrite = my_permission ∈ {write, manage}`
- settings 域内浅合并；不自动删除键以「解除冻结」
- 不自动 reingest；不做 grant UI / RRF 改动
- Conventional commits；分支 `fix/m6-permission-settings-merge`

---

### Task 1: resolve_kb_permission + KnowledgeBaseOut.my_permission

**Files:**
- Modify: `backend/app/modules/identity/permissions.py`
- Modify: `backend/app/modules/knowledge/schemas.py`
- Modify: `backend/app/modules/knowledge/service.py` (`_kb_out` 需 claims)
- Test: `backend/tests/test_kb_my_permission.py`（新建）

**Interfaces:**
- `async def resolve_kb_permission(session, *, tenant_id, user_id, role, kb) -> str | None`
- `KnowledgeBaseOut.my_permission: Literal["read","write","manage"] | None = None`
- `_kb_out(self, kb, *, claims: TokenClaims)` — 所有调用点传入 claims

- [x] **Step 1:** 失败测试：member+write grant → GET `my_permission==write`；owner → manage；tenant 可见无 grant → read
- [x] **Step 2:** 实现 resolve + schema + `_kb_out`
- [x] **Step 3:** pytest 通过
- [x] **Step 4:** Commit `feat(knowledge): KnowledgeBaseOut 返回 my_permission`

---

### Task 2: settings 浅合并

**Files:**
- Modify: `backend/app/modules/knowledge/settings_validate.py` — `shallow_merge_settings`
- Modify: `backend/app/modules/knowledge/service.py` update path
- Test: `backend/tests/test_kb_settings.py`

- [x] **Step 1:** 测试：已有 retrieval_rules，PATCH 仅 chunk max_tokens → 两者皆在
- [x] **Step 2:** 实现 merge + 服务层调用
- [x] **Step 3:** pytest + `make openapi`
- [x] **Step 4:** Commit `fix(knowledge): KB settings PATCH 按域浅合并`

---

### Task 3: 前端 canWrite + dirty settings payload

**Files:**
- Modify: `frontend/src/features/knowledge/api.ts`
- Modify: `frontend/src/features/knowledge/panels/KbFilesPanel.tsx`
- Modify: `frontend/src/features/knowledge/panels/KbSettingsPanel.tsx`
- `make openapi` if not done in Task 2

- [x] **Step 1:** `canWrite` 改用 `kb.my_permission`
- [x] **Step 2:** `buildSettingsPayload` 相对 baseline 只含脏键；无脏则不请求
- [x] **Step 3:** Settings 面板无写权限时禁用编辑
- [x] **Step 4:** `pnpm lint && pnpm typecheck`
- [x] **Step 5:** Commit `fix(frontend): 按 my_permission 门控并只提交脏 settings`

---

## 验证

```bash
cd backend && uv run pytest tests/test_kb_my_permission.py tests/test_kb_settings.py -q
cd frontend && pnpm lint && pnpm typecheck
```
