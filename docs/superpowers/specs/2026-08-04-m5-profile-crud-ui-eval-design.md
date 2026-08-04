# M5 切片 C/D 设计：Profile CRUD + 配置 UI → evaluate

> 状态：已批准并实施  
> 日期：2026-08-04  
> 分支：`feat/m5-profile-resolve`（可与 A/B 同 PR，或 C/D 分 PR）

## 0. 已确认决策

| 项 | 选择 |
| --- | --- |
| 顺序 | **先 C 后 D** |
| C 深度 | 最小可用：Admin tab + JSON 编辑 + KB 改绑 |
| 权限 | `owner\|admin` 可写；内置只读，仅「派生」；全员可读 GET |
| D 深度 | `evaluate.py` + 小 golden + Recall@k/MRR；CI 可选不阻断 |
| API 归属 | knowledge 模块扩展（对齐 `docs/03-api.md`） |
| UI 入口 | `/admin?tab=profiles` |

前置：切片 A/B 已提供 `resolve` + chat/search/chunk 消费。

---

## 1. 切片 C — Profile CRUD + 配置 UI

### 1.1 目标

租户管理员可从内置模板派生自定义行业配置，编辑规则 jsonb，并将知识库改绑到指定 profile；运行时仍走既有 `resolve()`。

### 1.2 非目标

- 删除 profile、完整表单/JSON 双视图
- `parse_rules` / `metadata_schema` 专项表单（可经 JSON 一并 PATCH，无单独 UX）
- 术语表上传、全局改写内置种子

### 1.3 API

#### `GET /industry-profiles`（保持）

- 认证用户可读；返回内置 + 本租户自定义。
- `IndustryProfileOut` 扩展字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id, code, name, is_builtin, tenant_id | 已有 | |
| chunk_rules | object | 已有（A） |
| prompt_overrides | object | 新增 |
| retrieval_rules | object | 新增 |
| parse_rules | object | 可选返回，便于 JSON 整包编辑 |
| metadata_schema | object | 可选返回 |

#### `POST /industry-profiles`（新建，admin+）

```json
{
  "base_code": "process_industry",
  "code": "acme_process_v1",
  "name": "ACME 流程",
  "chunk_rules": null,
  "prompt_overrides": null,
  "retrieval_rules": null,
  "parse_rules": null,
  "metadata_schema": null
}
```

行为：

1. 解析 `base_code`：优先本租户同 code，否则内置（与 `get_profile_by_code` 一致）。
2. 深拷贝各 jsonb；请求中非 null 的域覆盖副本。
3. 写入 `tenant_id=claims.tenant_id`，`is_builtin=false`。
4. `code` 在本租户内唯一；冲突 → `409`（`duplicate_profile_code`）。
5. 写入前用 `profile.schemas`（`ChunkRulesConfig` / `RetrievalRulesConfig` / `PromptOverridesConfig`）校验已知域；非法 → `400 validation_error`。

依赖：`Depends(require_role(ROLE_ADMIN))`（owner 满足阶梯）。

#### `PATCH /industry-profiles/{id}`（新建，admin+）

- 仅 `tenant_id == 当前租户` 且 `is_builtin == false`。
- 内置或跨租户：`404`（不泄露）或内置本租户可见时 `403`/`422`（`builtin_immutable`）——实现取：**查得到但是 builtin → 422 `builtin_immutable`；查不到 → 404**。
- 可更新：`name`、以及任意 jsonb 域（部分更新：只替换请求中出现的域）。
- 校验同 POST。

#### `PATCH /knowledge-bases/{kb_id}` 扩展

`KnowledgeBaseUpdate` 增加可选：

```text
profile_code: str | None
```

- 非 null 时解析为 `profile_id`（租户优先 / 内置回退）；找不到 → `422`。
- 权限：沿用现有 KB 更新（manage/write 可见性），**不额外要求 admin**（与建库选模板一致）。若现网 KB PATCH 已限 manage，保持不变。

### 1.4 后端落点

| 文件 | 变更 |
| --- | --- |
| `knowledge/schemas.py` | Create/Update/Out |
| `knowledge/repository.py` | create/update/get_by_id；code 唯一查询 |
| `knowledge/service.py` | 派生、校验、改绑 |
| `knowledge/router.py` | POST/PATCH profiles；KB update 透传 |
| `profile/schemas.py` | 复用校验（可不新增文件） |
| OpenAPI 导出 | 实施后跑 `export_openapi` / 前端 gen |

### 1.5 前端

| 项 | 说明 |
| --- | --- |
| `features/profiles/{api,hooks}.ts` | list / create / patch |
| `ProfilesPanel.tsx` | 表格 + 派生对话框 + JSON textarea 编辑 |
| `AdminPage` | tab `profiles`，门禁同 connections |
| `KbDetailPage` | 展示 profile + select 改绑 PATCH |
| OpenAPI 类型 | 同步 gen |

UI 文案：列表列 code / name / 内置·自定义；内置行仅「派生」；自定义行「编辑」。

### 1.6 测试（C）

- 派生成功；重复 code → 409
- PATCH 内置 → 422
- PATCH 自定义更新 `retrieval_rules.top_k` 后，对该 KB `resolve` 生效（可单测 service 层）
- KB `profile_code` 改绑更新 `profile_id`
- 可选：API 集成测（admin token）

### 1.7 验收（C）

1. Admin 可派生并 JSON 保存自定义 profile  
2. 知识库可改绑  
3. 改绑后 chat/search/chunk 行为随 resolve 变化（沿用 A/B）

---

## 2. 切片 D — evaluate（C 完成后）

### 2.1 目标

可重复的离线检索评测脚本 + 小样本 golden，输出基线指标；不阻断默认 CI。

### 2.2 非目标

- LLM-as-judge、SSE 生成评测
- 大标注集、CI 硬阈值阻断（>2pp）
- 替换 `compare_retrieval.py`（可并存；evaluate 更偏指标）

### 2.3 产物

```text
backend/evals/golden.jsonl   # 每行: query, kb_id?, expected_document_ids[] / expected_pages?
backend/scripts/evaluate.py  # login → POST /search → Recall@k, MRR → stdout + optional JSON
```

指标（最小）：

- Recall@k（k 默认 10，可 CLI）
- MRR（首个相关文档出现位置的倒数）

相关定义：命中 `expected_document_ids` 任一即相关（页级可选，有则加分字段但不强制）。

复用：`compare_retrieval.py` 的登录与 HTTP 客户端模式。

### 2.4 CI

- 默认：**不加**阻断 job；文档说明本地/手动运行方式。
- 可选后续：`workflow_dispatch` 非阻断步骤。

### 2.5 验收（D）

1. 对 fixture/本地环境跑通并打印指标  
2. golden 至少含数条可复现 query（可用 seed 文档或文档化占位 + skip-if-empty）

---

## 3. 风险与开放项

| 风险 | 缓解 |
| --- | --- |
| OpenAPI 漂移 | C 完成后强制 export + 前端 gen |
| 自定义 profile 被 KB 引用后「删不掉」 | 本切片无 DELETE，无此问题 |
| JSON 编辑易写坏 | 后端 Pydantic 校验 + 前端保存前 JSON.parse |
| evaluate 无真实数据 | golden 可带 skip；脚本对空集友好退出 |

无未决占位符；C/D 边界已切分。

---

## 4. 实施顺序

1. C 后端 API + 测试  
2. C OpenAPI + 前端 Admin tab + KB 改绑  
3. C progress 更新  
4. D evaluate + golden + 文档  
5. （可选）分 PR：`feat/m5-profile-crud-ui` / `feat/m5-evaluate`
