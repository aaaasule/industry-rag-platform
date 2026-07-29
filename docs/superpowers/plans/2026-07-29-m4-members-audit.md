# M4 Members + Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Backend closed-loop tenant membership CRUD + `audit_logs` table/API with hooks on members, grants, KB delete, login/switch-tenant.

**Architecture:** Extend `identity` for `/memberships`; new `audit` module with `AuditService.record()` (savepoint, never fail callers); hook call sites; migration `0005`.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Postgres RLS, httpx pytest.

**Spec:** `docs/superpowers/specs/2026-07-29-m4-members-audit-design.md`

## Global Constraints

- Admin+ only (`require_role(ROLE_ADMIN)`); no frontend; no invite email; known users only for add.
- Audit write failures must not break primary flows.
- Conventional commits; do not commit unless asked.

---

## File map

| Path | Role |
| --- | --- |
| `backend/alembic/versions/20260729_0005_audit_logs.py` | Table + RLS + indexes |
| `backend/app/modules/audit/{models,schemas,service,router,__init__}.py` | Audit module |
| `backend/app/modules/identity/repository.py` | Tenant membership list/add/update/delete helpers |
| `backend/app/modules/identity/membership_service.py` | Business rules |
| `backend/app/modules/identity/schemas.py` | Member request/response |
| `backend/app/modules/identity/memberships_router.py` | `/memberships` CRUD |
| `backend/app/modules/identity/service.py` + `router.py` | Login / switch-tenant audit hooks |
| `backend/app/modules/knowledge/service.py` | Grant + delete KB hooks |
| `backend/app/api.py` / `alembic/env.py` | Register routers + model import |
| `backend/tests/test_memberships.py` / `test_audit_logs.py` | Acceptance |
| `docs/07-progress.md` | Progress note |

---

### Task 1: Migration `0005_audit_logs`

- [x] Create migration revising `0004_message_feedbacks`
- [x] Columns per spec; indexes `(tenant_id, created_at DESC)`, `(tenant_id, action)`
- [x] `_enable_tenant_rls(["audit_logs"])`
- [x] `make migrate` (or alembic upgrade) locally when implementing

### Task 2: Audit module

- [x] ORM `AuditLog`
- [x] `AuditService.record(...)` with `begin_nested`, catch+warn
- [x] `GET /admin/audit-logs` + filters
- [x] Wire `api.py` + `env.py`

### Task 3: Memberships CRUD

- [x] Repo methods for tenant-scoped membership CRUD + owner count
- [x] `MembershipService` rules (last owner, admin vs owner, no self-delete)
- [x] Router with `require_role(ROLE_ADMIN)`
- [x] Audit on add/role_change/remove

### Task 4: Hooks

- [x] login + switch_tenant → `auth.*` (login: pass Request IP)
- [x] upsert_grant / delete_grant / delete_knowledge_base → `kb_grant.*` / `knowledge_base.delete`

### Task 5: Tests + docs

- [x] `test_memberships.py` + `test_audit_logs.py` covering design §9
- [x] Update `docs/07-progress.md`
- [x] Run targeted pytest

---

**Done when:** memberships CRUD + audit list work under admin+; hooks produce rows; member gets 403; tests green.
