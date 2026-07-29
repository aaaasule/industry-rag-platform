# M4 切片：模型接入点管理 + 用途路由（后端闭环）

> 状态：已批准，实现中  
> 日期：2026-07-30  
> 范围：后端 API + 迁移 + ProviderFactory 路由；**不含前端 / 用量 / 健康探测 Worker**

## 1. 目标

将 M0 全局 `IRP_*` Provider 升级为可管理的多接入点：

1. 租户 `admin+` 可 CRUD 本租户接入点、单独写凭证、连通性探测。
2. 平台级接入点由 seed 从环境变量初始化，租户只读。
3. chat / retrieval / ingestion Worker 经 `ProviderFactory` 按 purpose 路由；无库内接入点时回退 `build_*_provider(settings)`。

## 2. 已确认决策

| 项 | 选择 |
| --- | --- |
| 范围 | CRUD + test + 运行时路由（方案 B） |
| 凭证 | Fernet 加密入库，API 只写不读 |
| 层级 | 租户 CRUD + 平台 seed 兜底 |
| 覆盖 | API + Worker；无前端 |
| 架构 | 独立 `modelops` 模块 + `ProviderFactory` |

## 3. 非目标

- 前端接入点页 / 用量仪表盘
- `llm_usages` / hourlies / Redis 埋点
- 定时健康探测与按 `health=down` 自动故障转移
- 平台超管 CRUD、`model_pricing`
- JWT 吊销名单

## 4. 数据模型

迁移 `0006_model_connections`：

| 列 | 说明 |
| --- | --- |
| id | uuid PK |
| tenant_id | NULL=平台级；非空=租户自建 |
| name | 展示名 |
| provider_type | `openai_compatible` \| `fake` |
| base_url | 端点 |
| credential_cipher | Fernet 密文；fake 可空串 |
| credential_hint | 明文后 3 字符，掩码用 |
| model | 厂商模型 id |
| purposes | text[]：`chat` / `embedding` / `rerank` / `title` |
| priority | int，越小越优先，默认 100 |
| enabled | bool |
| health | `unknown`\|`healthy`\|`degraded`\|`down`（本切片主要写 unknown/healthy） |
| health_checked_at | timestamptz nullable |
| extra | jsonb（timeout 等），默认 `{}` |
| version | int，配置/凭证变更递增 |
| created_at / updated_at | |

索引：`(tenant_id, enabled, priority)` partial `WHERE enabled`。

RLS：`USING (tenant_id IS NULL OR tenant_id = app_current_tenant())`；`WITH CHECK (tenant_id = app_current_tenant())`（禁止应用角色写入平台行）。

加密密钥：`IRP_CREDENTIAL_SECRET`；local 若未设则从 `IRP_JWT_SECRET` 派生；非 local 必须显式设置。

## 5. API

前缀 `/api/v1`，均需 Bearer + 租户上下文；写操作与列表中的管理项需 `require_role(ROLE_ADMIN)`。

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| GET | `/model-connections` | 本租户 + 平台；凭证字段为掩码 `***xxx` |
| POST | `/model-connections` | 建租户点；body 含 `api_key`（fake 可省略） |
| PATCH | `/model-connections/{id}` | 改非凭证字段；`version++`；平台点 403 |
| PUT | `/model-connections/{id}/credential` | 只写 key；`version++` |
| POST | `/model-connections/{id}/test` | 最小实调；始终 HTTP 200 + `{ok,...}` |
| DELETE | `/model-connections/{id}` | 仅租户自建；平台 403 |
| GET | `/model-connections/routes` | 各 purpose 命中摘要（source: tenant\|platform\|env） |

审计：`model_connection.create|update|credential_update|delete|test`。

## 6. 路由算法

```
resolve(purpose, tenant_id):
  candidates = enabled ∧ purposes∋purpose
  1. tenant_id = 当前租户，order by priority ASC, id
  2. else tenant_id IS NULL，同样排序
  3. else Settings → build_*_provider
```

本切片**不**按 health 跳过节点。`ProviderFactory` 缓存键 `(connection_id, version, purpose_kind)`。

## 7. 运行时接线

- 废弃「仅 lifespan 全局单例」作为唯一来源；保留 env 构建函数供兜底与测试。
- FastAPI：请求内按 `claims.tenant_id` + purpose 取 Provider（chat→chat，search embedding→embedding，rerank→rerank）。
- Celery ingestion：任务内开 DB session，按文档所属 `tenant_id` resolve embedding。
- Seed：若不存在平台级 chat/embedding/rerank，从当前 `IRP_*` 各写一条（cipher 加密 api_key）。

## 8. 测试要点

- member 403；admin CRUD 租户点
- 列表凭证掩码；GET 永不返回明文
- 不可改/删平台点
- 同 purpose 租户点优先于平台点；无库配置时 env 兜底
- test 假 provider 返回 ok；错误密钥仍 200 + ok=false
- 改配置后 version 递增且缓存失效（行为测）

## 9. 文件清单

- `backend/alembic/versions/20260730_0006_model_connections.py`
- `backend/app/modules/modelops/`（models, schemas, credentials, repository, service, router, provider_factory）
- `backend/app/platform/llm/factory.py` — `build_*_from_connection`
- `backend/app/platform/config.py` — `credential_secret`
- 接线：`api.py`、`chat`/`retrieval` deps、`ingestion/tasks.py`、`scripts/seed.py`
- `backend/tests/test_model_connections.py`
- `docs/07-progress.md`
