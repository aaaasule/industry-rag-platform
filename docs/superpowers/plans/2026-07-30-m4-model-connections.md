# M4 Model Connections Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans or implement task-by-task. Steps use checkbox syntax.

**Goal:** Tenant-managed model connections with encrypted credentials, purpose routing via ProviderFactory, env fallback; API + Worker wired; no frontend/usage.

**Architecture:** New `modelops` module; `ProviderFactory.resolve(purpose, tenant_id)`; platform rows seeded from `IRP_*`.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Fernet, Celery worker.

**Spec:** `docs/superpowers/specs/2026-07-30-m4-model-connections-design.md`

---

### Task 1: Migration + ORM + crypto

- [x] `0006_model_connections` + RLS
- [x] `ModelConnection` ORM
- [x] `credentials.py` encrypt/decrypt/mask
- [x] Settings `credential_secret`

### Task 2: modelops service + API

- [x] repository / schemas / service / router
- [x] Register in `api.py`; audit hooks
- [x] Tests for CRUD / mask / platform readonly

### Task 3: ProviderFactory + build_from_connection

- [x] `build_*_from_connection` in factory.py
- [x] `ProviderFactory` with cache + resolve order
- [x] `/model-connections/routes` + `/test`

### Task 4: Wire runtime

- [x] chat / retrieval request-scoped providers
- [x] ingestion worker resolve by tenant
- [x] seed platform connections from env
- [x] Update `docs/07-progress.md`
- [x] Run tests

**Done when:** admin can manage tenant connections; routing prefers tenant→platform→env; worker uses same resolve; tests green.
