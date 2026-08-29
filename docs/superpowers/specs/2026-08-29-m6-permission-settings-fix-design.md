# M6 验收修复：my_permission 与 settings 浅合并

> 状态：待用户审阅  
> 日期：2026-08-29  
> 前置：M6 已合入 `main`（PR #35）  
> 决策：写权限用 `KnowledgeBaseOut.my_permission`；settings 只提交脏键 + 后端按域浅合并

## 0. 已确认决策

| 项 | 选择 |
| --- | --- |
| 写权限信号 | `KnowledgeBaseOut.my_permission: read \| write \| manage \| null` |
| 前端门控 | `canWrite = my_permission ∈ {write, manage}`，不再仅用租户 role |
| settings 写入 | PATCH **浅合并**（`chunk_rules` / `retrieval_rules` 各自浅合并） |
| 脏字段 | 相对表单基线（`settings ∪ effective`）只提交变更键 |
| 解除冻结 | **本轮不做**「改回与 effective 相同则删除 settings 键」 |
| 非目标 | grant UI 重构、RRF、查询扩展、自动 reingest |

## 1. 问题

1. `KbFilesPanel` 用 `role === owner|admin` 判断 `canWrite`，有 KB `write`/`manage` 授权的 `member`（及创建者已是 member 租户角色时）被误灰，与后端 `PERM_WRITE` 不一致。  
2. 配置页 `buildSettingsPayload` 整包写入 `settings`，且后端 `kb.settings = validate(...)` **整包替换**，未改动的字段也会从 effective「冻」进本库，之后改 Profile 不再影响这些键。

## 2. 权限：`my_permission`

### 2.1 计算规则（与 `visible_kb_ids` 对齐）

对单个 `KnowledgeBase` + `TokenClaims`：

| 条件 | `my_permission` |
| --- | --- |
| 租户 role 为 owner / admin | `manage` |
| `created_by == user_id` | `manage` |
| 存在 grant | grant 的 `permission`（`read`/`write`/`manage`） |
| `visibility == tenant` 且无更高权限 | `read` |
| 否则（不应出现在列表里） | `null` |

抽公共函数（建议放 `identity/permissions.py`）：

```python
async def resolve_kb_permission(
    session, *, tenant_id, user_id, role, kb: KnowledgeBase
) -> str | None: ...
```

`_kb_out` 在组装 `KnowledgeBaseOut` 时填入；list/get/create/update 均走 `_kb_out`，故 naturally 带上字段。

### 2.2 前端

- `KnowledgeBase.my_permission` 类型同步（`make openapi`）  
- `KbFilesPanel`：`canWrite = kb?.my_permission === 'write' || kb?.my_permission === 'manage'`  
- 加载中无 kb：写操作保持 disabled  
- `KbSettingsPanel`：无写权限时禁用保存按钮与可编辑控件（只读展示）

## 3. Settings 浅合并

### 3.1 后端

`update_knowledge_base` 当 `payload.settings is not None`：

1. `incoming = validate_kb_settings(payload.settings)`（白名单 + 值类型不变）  
2. `merged = shallow_merge_settings(kb.settings or {}, incoming)`  
3. `kb.settings = merged`

```python
def shallow_merge_settings(existing: dict, incoming: dict) -> dict:
    out = dict(existing)
    for domain in ("chunk_rules", "retrieval_rules"):
        if domain not in incoming:
            continue
        base = dict(out.get(domain) or {}) if isinstance(out.get(domain), dict) else {}
        patch = incoming[domain] if isinstance(incoming[domain], dict) else {}
        base.update(patch)
        out[domain] = base
    # 忽略其他顶层键（validate 已拒）
    return out
```

**契约变更**：客户端若依赖「PATCH settings 整包替换清空未传域」，需改为显式传空对象——当前前端从未依赖该行为；OpenAPI/注释标明「域内浅合并」。

不自动 reingest（保持 M6 约定）。

### 3.2 前端

`buildSettingsPayload(chunk, retrieval, baseline)`：

- 比较 `chunk` / `retrieval` 与 `rulesFromKb` 基线  
- 仅把变化的键放入 `chunk_rules` / `retrieval_rules`  
- 若某域无任何脏键，则省略该域  
- 若两域皆空：不发起 PATCH（或 toast「无变更」）

`rerank: default`：若基线也是 default（settings 中无 `rerank_enabled`），不写；若基线为 on/off 而用户改回 default——本轮仍不删除键（非目标）；仅当用户在 on↔off 或与基线不同时写入。

## 4. 测试

| 用例 | 期望 |
| --- | --- |
| member + grant write，GET KB | `my_permission == write` |
| member 无 grant、tenant 可见 | `my_permission == read` |
| owner | `my_permission == manage` |
| PATCH settings 只含 `chunk_rules.max_tokens` | 原 `retrieval_rules` 保留；`max_tokens` 更新 |
| 前端脏字段 | 单元或组件级可选；至少后端集成测 |

## 5. 验收

1. 被授予 write 的 member：文件页可开关启用、批量、上传；只读 member 仍灰。  
2. 只改 Top-K 后保存：DB `settings` 不含未改动的 `max_tokens` 等冻结值（若此前 settings 为空）。  
3. `pnpm lint && typecheck`；相关 pytest 绿；`make openapi`。

## 6. PR

单分支 `fix/m6-permission-settings-merge`，一个 PR 合入。
