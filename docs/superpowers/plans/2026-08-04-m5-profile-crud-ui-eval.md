# M5 C/D Implementation Plan

> **For agentic workers:** 先完成 C 全部任务，再做 D。规格：`docs/superpowers/specs/2026-08-04-m5-profile-crud-ui-eval-design.md`

**Goal:** 租户可派生/编辑行业 profile 并改绑 KB；随后提供最小检索评测脚本。

**Architecture:** knowledge 模块扩 POST/PATCH；Admin tab JSON 编辑；evaluate 复用 HTTP search。

**Tech Stack:** FastAPI, React/Vite, Pydantic profile schemas

## Global Constraints

- 内置只读；写操作 `require_role(ROLE_ADMIN)`
- 多 KB resolve 仍取首个（A/B）
- D：CI 不阻断

---

### Task 1: Backend profile CRUD

**Files:** `knowledge/schemas.py`, `repository.py`, `service.py`, `router.py`, `tests/test_profile_crud.py`

- [ ] IndustryProfileCreate/Update/Out 扩展
- [ ] repo get_by_id / create / tenant code unique
- [ ] service derive + patch + validate via ChunkRulesConfig 等
- [ ] router POST/PATCH + require_role
- [ ] KB update profile_code
- [ ] 测试

### Task 2: Frontend Admin + KB 改绑

**Files:** `features/profiles/*`, `AdminPage.tsx`, `KbDetailPage.tsx`, openapi gen

- [ ] api/hooks/ProfilesPanel
- [ ] admin tab profiles
- [ ] KbDetail 改绑

### Task 3: evaluate (D)

**Files:** `backend/evals/golden.jsonl`, `backend/scripts/evaluate.py`, progress

- [ ] script + golden + docs/progress

---

执行：本会话 **Inline** 连续落地 C→D。
