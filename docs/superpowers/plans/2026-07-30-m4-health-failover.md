# M4 Health 故障转移 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 定时探测接入点健康状态，路由跳过 `down` 并按 priority 故障转移，全 down 时回退 env。

**Architecture:** 抽出 `probe_connection`；Celery Beat 每 300s 扫 enabled 行写 health；`ProviderFactory.resolve_connection` 过滤 `down`；`/test` 失败写 `down`。

**Tech Stack:** FastAPI、SQLAlchemy asyncio、Celery Beat、现有 Fake/OpenAI-compatible Provider。

## Global Constraints

- 无新迁移；沿用 `model_connections.health`
- 业务请求失败不改 health；本切片不写 `degraded`
- 路由仅跳过 `health == 'down'`；`unknown`/`healthy`/`degraded` 可用
- 定时探测用 migration DB URL 绕过 RLS；不写 audit_logs
- 响应中文仓库惯例；测试用 Fake provider

---

## File map

| 文件 | 职责 |
| --- | --- |
| `backend/app/modules/modelops/probe.py` | `ProbeResult` + `probe_connection(row, settings)` |
| `backend/app/modules/modelops/health_tasks.py` | `probe_all_connections` + Celery task |
| `backend/app/modules/modelops/provider_factory.py` | resolve 过滤 down |
| `backend/app/modules/modelops/service.py` | test 用 probe；失败→down |
| `backend/app/worker.py` | import health_tasks + beat 300s |
| `backend/tests/test_health_failover.py` | 路由/test/probe 测试 |
| `docs/07-progress.md` | 进度 |

---

### Task 1: probe_connection + /test 对齐 down

**Files:**
- Create: `backend/app/modules/modelops/probe.py`
- Modify: `backend/app/modules/modelops/service.py`（`test` 改用 probe，失败写 `HEALTH_DOWN`）
- Test: `backend/tests/test_health_failover.py`

**Interfaces:**
- Produces: `ProbeResult(ok: bool, latency_ms: float, error_message: str | None)`；`async def probe_connection(row: ModelConnection, *, settings: Settings | None = None) -> ProbeResult`

- [ ] **Step 1: 实现 probe.py**

```python
@dataclass(frozen=True, slots=True)
class ProbeResult:
    ok: bool
    latency_ms: float
    error_message: str | None = None

async def probe_connection(row: ModelConnection, *, settings: Settings | None = None) -> ProbeResult:
    # purposes[0] → embedding | rerank | chat(ping)；异常 → ok=False
```

逻辑从现有 `ModelOpsService.test` 抽出；`settings or get_settings()`。

- [ ] **Step 2: service.test 改用 probe；失败 HEALTH_DOWN**

成功：`HEALTH_HEALTHY`；失败：`HEALTH_DOWN`（替换现 `HEALTH_UNKNOWN`）；保留审计。

- [ ] **Step 3: 测试 /test 失败写 down**

用无效 base_url 的 openai_compatible 点，或 monkeypatch `probe_connection` 返回失败；断言 DB `health == "down"`。

- [ ] **Step 4: 跑测**

`cd backend && uv run pytest tests/test_health_failover.py::test_manual_test_failure_marks_down -q`

- [ ] **Step 5: Commit**

`feat(m4): 抽出 probe 并让 /test 失败标记 down`

---

### Task 2: ProviderFactory 跳过 down

**Files:**
- Modify: `backend/app/modules/modelops/provider_factory.py`（`resolve_connection`）
- Test: `backend/tests/test_health_failover.py`

**Interfaces:**
- Consumes: `ModelConnection.health`；`HEALTH_DOWN` 常量
- Produces: 过滤后的 resolve；无可用 → `(None, "env")`

- [ ] **Step 1: 写失败测试**

建两个 chat 租户点：priority 1=`down`，priority 2=`healthy`；assert resolve 命中第二；两条都 down → source env。

- [ ] **Step 2: resolve 过滤**

```python
rows = await self._repo.list_for_purpose(...)
usable = [r for r in rows if r.health != HEALTH_DOWN]
if not usable:
    return None, "env"
row = usable[0]
...
```

- [ ] **Step 3: 跑测通过并 commit**

`feat(m4): 路由跳过 down 接入点并回退 env`

---

### Task 3: Celery 定时探测

**Files:**
- Create: `backend/app/modules/modelops/health_tasks.py`
- Modify: `backend/app/worker.py`
- Test: `backend/tests/test_health_failover.py`

**Interfaces:**
- Produces: `async def probe_all_connections() -> dict[str, int]`（probed/healthy/down）；task `modelops.probe_connections`

- [ ] **Step 1: probe_all_connections**

迁移 URL 开 session；`select enabled`；逐个 `probe_connection` 写 health/checked_at；末尾 `clear_provider_cache()`；返回计数。

- [ ] **Step 2: Celery task + beat 300s queue=stats**

- [ ] **Step 3: 测试 fake 点 probe 后 healthy**

- [ ] **Step 4: Commit**

`feat(m4): 定时探测接入点健康状态`

---

### Task 4: 进度文档 + 收尾验证

**Files:**
- Modify: `docs/07-progress.md`

- [ ] **Step 1: 更新当前状态与完成表**
- [ ] **Step 2: 跑相关测试**

`uv run pytest tests/test_health_failover.py tests/test_model_connections.py -q`

- [ ] **Step 3: Commit**

`docs: 记录 M4 health 故障转移进度`

---

## Spec coverage

| Spec 要求 | Task |
| --- | --- |
| probe.py | 1 |
| /test → down | 1 |
| resolve 跳过 down / env | 2 |
| Celery + beat 300s | 3 |
| clear cache | 3 |
| 测试要点 | 1–3 |
| 07-progress | 4 |
