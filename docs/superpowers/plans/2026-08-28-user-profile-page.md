# 个人资料页 Implementation Plan

> **For agentic workers:** 按任务顺序实现；每任务有验证步骤。Spec: `docs/superpowers/specs/2026-08-28-user-profile-page-design.md`

**Goal:** 交付 `/settings/profile`：改显示名、改密码、租户列表/切换；侧栏头像入口。

**Architecture:** identity 模块新增 `PATCH /auth/me` 与 `POST /auth/change-password`；前端 `ProfilePage` + hooks；会话缓存用 React Query 失效。

**Tech Stack:** FastAPI / SQLAlchemy / React / TanStack Query / 现有 UI 组件。

---

### Task 1: 后端 API + 测试
- schemas / service / router
- `tests/test_auth_api.py` 补充用例

### Task 2: 前端页面 + 入口
- `api.ts` / `hooks.ts` / `ProfilePage.tsx` / routes / AppLayout 链接
