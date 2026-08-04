# Usage Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付客户可演示的用量仪表盘（七图 + summary），含薄后端补齐与 OpenAPI 同步。

**Architecture:** 后端扩展 series/breakdown；前端 `features/usages` 用三类 API + model-connections；Recharts 渲染；admin 导航门禁。

**Tech Stack:** FastAPI、React 18、TanStack Query、recharts、openapi-typescript、Tailwind。

## Global Constraints

- 时区必传，默认 `Asia/Shanghai`；前端不做日聚合换算
- 图表只消费 hourlies（user/kb breakdown 例外走明细）
- 仅 admin/owner；member 403 / 隐藏导航
- 先 OpenAPI 再生页面类型

---

### Task 1: 后端 latency + user/kb breakdown

**Files:**
- Modify: `backend/app/modules/modelops/usage_schemas.py`
- Modify: `backend/app/modules/modelops/usage_service.py`
- Modify: `backend/app/modules/modelops/usage_router.py`
- Test: `backend/tests/test_usage_metering.py`

- [ ] **Step 1:** 扩展测试：series 含 `latency_p95_ms`；breakdown `dimension=user`
- [ ] **Step 2:** 实现 schema / service / router
- [ ] **Step 3:** 跑通相关测试

### Task 2: OpenAPI + 前端 API 层

**Files:**
- Modify: `frontend/src/types/openapi.json` / `openapi.gen.ts`
- Create: `frontend/src/features/usages/api.ts`, `hooks.ts`

- [ ] **Step 1:** 导出 OpenAPI 并 `pnpm gen:api`
- [ ] **Step 2:** 封装 summary/series/breakdown + listConnections
- [ ] **Step 3:** TanStack Query hooks（共享 filter key）

### Task 3: 页面骨架与七图

**Files:**
- Create: `frontend/src/features/usages/UsageDashboardPage.tsx` 及图表子组件
- Modify: `frontend/src/app/routes.tsx`, `AppLayout.tsx`
- Modify: `frontend/package.json`（recharts）

- [ ] **Step 1:** 安装 recharts；路由 `/usages`；导航角色过滤
- [ ] **Step 2:** 筛选条 + summary 卡片
- [ ] **Step 3:** 七图 + 空态/加载/`stale_until`
- [ ] **Step 4:** `pnpm typecheck` / lint

### Task 4: 进度与收尾

**Files:**
- Modify: `docs/07-progress.md`

- [ ] **Step 1:** 更新当前状态与完成记录
- [ ] **Step 2:** 本地自测清单勾选

---
