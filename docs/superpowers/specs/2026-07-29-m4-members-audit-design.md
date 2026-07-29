# M4 切片：成员管理 + 审计日志（后端闭环）

> 状态：设计稿（待实现）  
> 日期：2026-07-29  
> 范围：仅后端 API + 迁移 + 测试；**不含前端页面**

## 1. 目标

补齐多租户运营的两条能力：

1. **成员管理**：租户 `admin` / `owner` 可按邮箱将已存在用户加入本租户、改角色、移出。
2. **审计日志**：关键写操作落库，供 `admin` / `owner` 查询。

对齐 `docs/02-data-model.md` §4.9、`docs/03-api.md` 管理接口、`docs/06-roadmap.md` M4。

## 2. 非目标

- 前端成员页 / 审计页
- 邀请邮件、邮件通知、按邮箱自动创建用户
- 模型配置运营、用量看板（M4 后续切片）
- 文档上传 / 重新入库等全量操作审计（本切片不覆盖，避免噪声）

## 3. 架构

```
identity/          ← 扩展：MembershipService + /memberships CRUD
audit/             ← 新建模块：AuditLog 模型、AuditService.record、GET /admin/audit-logs
knowledge/         ← 钩子：grant 变更、delete KB 时写审计
identity/service   ← 钩子：login、switch_tenant 写审计
```

权限：统一 `Depends(require_role(ROLE_ADMIN))`（`admin` 与 `owner` 均 ≥ admin）。

审计写入失败 **不得阻断** 主业务（`record` 吞异常并打 `warning` 日志），避免审计表故障拖垮登录/删库。

## 4. 数据模型

### 4.1 `audit_logs`（迁移 `0005_audit_logs`）

与 `docs/02` 对齐：

| 列 | 类型 | 说明 |
| --- | --- | --- |
| id | uuid PK | |
| tenant_id | uuid NOT NULL | RLS 租户隔离；登录成功时写目标租户 |
| actor_id | uuid NULL | 操作者；登录失败可不记（本切片仅记成功登录） |
| action | text NOT NULL | 见 §6 |
| target_type | text NOT NULL | `membership` / `kb_grant` / `knowledge_base` / `session` |
| target_id | uuid NULL | 目标实体 id |
| payload | jsonb NOT NULL DEFAULT `{}` | 变更摘要（角色、邮箱、visibility 等） |
| ip | inet NULL | 可选；本切片登录可从 Request 取，其余可为 null |
| created_at | timestamptz | |

索引：`(tenant_id, created_at DESC)`、`(tenant_id, action)`。

RLS：`tenant_isolation` 策略（与既有表一致）。

**不设 FK 到 users**（actor 删除后日志仍保留）。

### 4.2 `memberships`

沿用现有表，无 schema 变更。

## 5. 成员管理 API

前缀：`/api/v1`（与现有一致）。均需 Bearer + `X-Tenant-Id`，且角色 ≥ `admin`。

### 5.1 `GET /memberships`

列出**当前租户**全部成员（含自己）。

响应：

```json
{
  "items": [
    {
      "user_id": "uuid",
      "email": "a@example.com",
      "display_name": "Alice",
      "role": "member",
      "created_at": "..."
    }
  ]
}
```

按 `created_at` 升序。

### 5.2 `POST /memberships`

Body：`{ "email": "b@example.com", "role": "member" }`

规则：

- `email` 必须已在 `users` 表存在，否则 **404** `user not found`。
- `role` ∈ `{member, admin, owner}`；默认 `member`。
- 若该用户已是本租户成员 → **409** `already a member`。
- 成功 → **201**，返回成员项。
- 写审计：`membership.add`。

### 5.3 `PATCH /memberships/{user_id}`

Body：`{ "role": "admin" }`

规则：

- 目标必须是本租户成员，否则 **404**。
- **不能**把租户内最后一个 `owner` 降级为非 owner → **400** `cannot demote the last owner`。
- `admin` **不能**将他人升为 `owner`，也 **不能**修改 `owner` 的角色 → **403**（仅 `owner` 可操作涉及 owner 的升降）。
- `owner` 可任意改角色（仍受「最后一个 owner」约束）。
- 写审计：`membership.role_change`，payload 含 `from`/`to`。

### 5.4 `DELETE /memberships/{user_id}`

规则：

- 目标必须是本租户成员，否则 **404**。
- **不能**删除最后一个 `owner` → **400** `cannot remove the last owner`。
- **不能**删除自己 → **400** `cannot remove yourself`（避免锁死会话；若需退出请另建流程）。
- `admin` **不能**删除 `owner` → **403**。
- 写审计：`membership.remove`。

## 6. 审计 action 约定

| action | target_type | 触发点 | payload 示例 |
| --- | --- | --- | --- |
| `membership.add` | membership | POST /memberships | `{email, role, user_id}` |
| `membership.role_change` | membership | PATCH | `{user_id, from, to}` |
| `membership.remove` | membership | DELETE | `{user_id, email, role}` |
| `kb_grant.create` | kb_grant | POST .../grants | `{grant_id, kb_id, grantee_*, permission}` |
| `kb_grant.update` | kb_grant | PATCH | `{grant_id, changes}` |
| `kb_grant.delete` | kb_grant | DELETE | `{grant_id, kb_id}` |
| `knowledge_base.delete` | knowledge_base | DELETE /knowledge-bases/{id} | `{name}` |
| `auth.login` | session | POST /auth/login 成功 | `{email}`；ip 填客户端 IP |
| `auth.switch_tenant` | session | POST /auth/switch-tenant | `{from_tenant_id, to_tenant_id}` |

## 7. 审计查询 API

### `GET /admin/audit-logs`

依赖：`require_role(ROLE_ADMIN)`。

Query：

| 参数 | 说明 |
| --- | --- |
| `action` | 可选，精确匹配 |
| `actor_id` | 可选 |
| `from` | 可选，ISO 时间，`created_at >=` |
| `to` | 可选，`created_at <` |
| `limit` | 默认 50，最大 200 |
| `offset` | 默认 0 |

响应：

```json
{
  "items": [
    {
      "id": "uuid",
      "actor_id": "uuid|null",
      "action": "membership.add",
      "target_type": "membership",
      "target_id": "uuid|null",
      "payload": {},
      "ip": "127.0.0.1|null",
      "created_at": "..."
    }
  ],
  "total": 123
}
```

按 `created_at DESC`。`total` 为过滤后的总数（便于分页）。

## 8. AuditService

```python
async def record(
    session,
    *,
    tenant_id: UUID,
    actor_id: UUID | None,
    action: str,
    target_type: str,
    target_id: UUID | None = None,
    payload: dict | None = None,
    ip: str | None = None,
) -> None:
    """写入一条审计；异常仅记日志，不抛出。"""
```

- 独立 `flush`（不强制要求与业务同事务提交成功才可见——与业务同 session 时随请求 commit 一起提交；若希望失败隔离，可用 `begin_nested`/单独 session；**首期：同请求 session，随业务 commit**，`record` 内 try/except 包住 insert+flush，失败 rollback 到 savepoint 或仅 log 后不 re-raise）。
- 推荐实现：`async with session.begin_nested():` 写入，失败只 warning，外层事务继续。

## 9. 测试计划

| 用例 | 期望 |
| --- | --- |
| member 调 GET /memberships | 403 |
| admin 列出成员 | 200，含 seed 用户 |
| POST 未知邮箱 | 404 |
| POST 已存在用户入租户 | 201；再 POST 409 |
| 降级最后一个 owner | 400 |
| admin 试图改 owner 角色 | 403 |
| DELETE 自己 | 400 |
| DELETE 成员 | 200；审计有 membership.remove |
| grant CRUD | 各写一条 kb_grant.* |
| delete KB | knowledge_base.delete |
| login | auth.login |
| switch-tenant | auth.switch_tenant |
| GET /admin/audit-logs | admin 可见；member 403 |
| action 过滤 | 只返回匹配项 |

## 10. 文件清单（预期）

- `backend/alembic/versions/20260729_0005_audit_logs.py`
- `backend/app/modules/audit/`（models, schemas, service, router, __init__）
- `backend/app/modules/identity/membership_service.py`（或扩 service）
- `backend/app/modules/identity/router.py` — memberships 路由
- `backend/app/modules/knowledge/service.py` / `router.py` — 审计钩子
- `backend/app/api.py` — 挂载 audit router
- `backend/tests/test_memberships.py`、`test_audit_logs.py`
- `docs/07-progress.md` 更新

## 11. 与既有文档差异说明

- `docs/03` 仅写了 `GET /admin/audit-logs`；本切片补全成员 CRUD 与审计 action 约定，实现后可回写 `docs/03` / `docs/07`。
- 登录审计的 `tenant_id`：取登录后默认租户（memberships 中 rank 最高者），与签发 JWT 一致。
