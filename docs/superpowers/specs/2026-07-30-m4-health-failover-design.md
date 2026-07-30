# M4 切片：接入点健康探测与故障转移

> 状态：已批准  
> 日期：2026-07-30  
> 顺序：用量埋点之后；本切片完成后 → 配额 / 前端仪表盘等可另开

## 1. 目标

- 定时探测所有 `enabled` 接入点，写入 `health` / `health_checked_at`
- `ProviderFactory` 解析时跳过 `health=down`，按 priority 切备用
- 全部不可用时回退 env `IRP_*` Provider
- 手动 `POST .../test` 与探测语义对齐：成功=`healthy`，失败=`down`

## 2. 已确认决策

| 项 | 选择 |
| --- | --- |
| 范围 | B：定时探测 + 路由故障转移；无前端 |
| 业务失败 | A：不改 `health` |
| 全 down | C：跳过 down → 无候选则 env |
| 状态语义 | A：成功=`healthy`，失败=`down`；本切片不写 `degraded`；路由仅跳过 `down` |
| `/test` | A：失败也写 `down` |
| 架构 | 方案 1：Celery Beat + 复用探针逻辑 + resolve 过滤 |

## 3. 非目标

- 用量仪表盘 / 接入点管理前端
- 业务请求失败熔断改 health
- `degraded` 延迟阈值
- 配额 429、新表迁移
- 探测结果写 Redis 双真相源

## 4. 数据与状态

沿用 `model_connections.health`：

| 值 | 本切片行为 |
| --- | --- |
| `healthy` | 探测/test 成功 |
| `down` | 探测/test 失败；**路由跳过** |
| `unknown` | 新建默认；路由**可用** |
| `degraded` | 本切片不写入；若历史存在则路由仍可用 |

无 schema 变更。

## 5. 组件

| 文件 | 职责 |
| --- | --- |
| `modelops/probe.py` | `probe_connection(row) → ProbeResult`；按 `purposes[0]` 调 embed/rerank/chat（与现有 `test` 同源） |
| `modelops/health_tasks.py` | Celery `modelops.probe_connections`：迁移角色列出 `enabled`，逐个 probe 写库 |
| `provider_factory.py` | `resolve_connection` 过滤 `health != down` |
| `service.py` | `/test` 失败写 `HEALTH_DOWN`；成功仍 `HEALTH_HEALTHY` |
| `worker.py` | Beat：每 300s，`queue=stats` |

探测会话用 `database_migration_url`（或 fallback `database_url`）绕过 RLS，以便更新平台级行。

## 6. 路由算法（更新）

```
resolve(purpose, tenant_id):
  candidates = enabled ∧ purposes∋purpose
               租户点优先，同层 priority ASC, id ASC
  usable = [c for c in candidates if c.health != 'down']
  if usable:
    return usable[0], tenant|platform
  return None, env   # build_*_provider(settings)
```

`GET /model-connections/routes` 走同一 `resolve`，无需新 API。

## 7. 定时探测

- 任务名：`modelops.probe_connections`
- 调度：300 秒（与路线图「约 5 分钟」一致）
- 单点失败：该点 `down`，继续后续点；任务返回探测计数
- 不写 `audit_logs`（避免每 5 分钟刷审计）；结构化日志即可
- 一轮结束后可 `clear_provider_cache()` 一次，避免长期持有已 down 节点的 Provider（可选但建议做）

## 8. 手动 `/test`

- 成功：`health=healthy`，`health_checked_at=now`
- 失败：`health=down`（由现 `unknown` 改为 `down`），仍 HTTP 200 + `{ok:false,...}`
- 保留审计 `model_connection.test`

## 9. 测试要点

- 租户主点 `down` + 备点 `healthy` → resolve/routes 命中备点
- 同 purpose 全部 `down` → source=`env`
- `/test` 失败 → `health=down`
- `probe_connections` 对 fake 接入点写 `healthy`
- `unknown` 点仍可被选中（不因 unknown 跳过）

## 10. 文件清单（预期）

- `backend/app/modules/modelops/probe.py`（新）
- `backend/app/modules/modelops/health_tasks.py`（新）
- `backend/app/modules/modelops/provider_factory.py`（改）
- `backend/app/modules/modelops/service.py`（改 test）
- `backend/app/worker.py`（beat）
- `backend/tests/test_health_failover.py`（新）
- `docs/07-progress.md`
