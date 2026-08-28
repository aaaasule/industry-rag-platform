# M6 知识库运营与检索智能化设计

> 状态：待评审  
> 日期：2026-08-28  
> 范围：四周全量（W1 运营 → W2 KB 调参 → W3 查询理解 → W4 行业打磨）  
> 前置：M0–M5 已合入；知识库四 Tab 工作台（PR #32）；`knowledge_bases.settings` 与 Profile 四级合并已存在

## 0. 已确认决策

| 项 | 选择 |
| --- | --- |
| 周期 | **四周全量**，按周拆 PR，不一次合巨型分支 |
| 文档禁用 | 列表仍可见；检索/问答排除；默认 `enabled=true` |
| 批量上限 | 单次最多 **50** 个文档，且必须属于同一 `kb_id` |
| KB 调参 | 写入已有 `knowledge_bases.settings`；**不**自动 reingest |
| 融合公式 | **不改** RRF 权重、不加相似度 cutoff API |
| 指代消解 | 走当前会话 Chat LLM；失败回退原 query |
| 查询扩展 | Profile/KB `retrieval_rules.query_expand`，默认 **false**；Playground 可单次打开 |
| 行业评测 | CI 仍用 `golden.ci.jsonl`；行业 golden **本地** `make eval`，不把真实语料硬失败绑进 CI |
| 明确不做 | 图谱 / RAPTOR / Agent / SSO / 图纸多模态 / 文档多 KB 复用 / 独立向量库 |

## 1. 目标

让运营人员能 **关掉过期资料、批量重试、在本库覆盖切块/召回参数、多轮口语能检索到正确条款**，并用三条内置模板的 golden 做本地回归。

## 2. 非目标

- 向量/全文权重滑条、RRF `k` 可配
- 知识图谱、RAPTOR、PageIndex、外部数据源同步
- SSO、密级、chunk 级 ACL
- HTML 解析器、扫描件表格专用引擎
- 改 `settings` 后自动全库重解析

## 3. 现状可复用

- `documents` 无 `enabled`；检索已 join `Document` 并过滤 `deleted_at` / `status=ready`。
- `knowledge_bases.settings` jsonb 已存在；`ProfileService.merge_*` 已实现 **KB.settings > Profile > 默认**。
- `KnowledgeBaseOut` / PATCH **尚未**暴露 `settings`。
- `SearchResult.rewritten_query` 目前等于 `normalize(query)`，无 LLM 改写。
- 审计目前覆盖授权/删库/登录等，**不含**文档上传/删除/摄取失败。
- 前端文件表无多选、无启用开关；配置页切块规则只读。

## 4. 数据与 API

### 4.1 文档启用

迁移 `0010_document_enabled`：`documents.enabled boolean NOT NULL DEFAULT true`。

检索 SQL 增加 `Document.enabled.is_(True)`（`vector_search` / `fulltext_search`）。

`PATCH /documents/{doc_id}`：

```json
{ "enabled": false, "metadata": { "equipment_model": "HYD-2201" } }
```

权限：`PERM_WRITE`。`metadata` 按当前 KB 的 `EffectiveProfile.metadata_schema` 校验（与登记时相同）。

`DocumentOut` 增加 `enabled`、`chunk_count`、`metadata`。`chunk_count` 列表接口用聚合查询，不新增计数列。

### 4.2 批量操作

`POST /knowledge-bases/{kb_id}/documents/batch`

```json
{ "action": "delete" | "reingest", "document_ids": ["..."] }
```

- `len(document_ids)` ∈ [1, 50]
- 非本库或已软删 → 404（与单条一致，避免探测）
- 响应：`{ "accepted": N, "job_ids": { "doc_id": "job_id"|null } }`（delete 的 job_ids 可空）

### 4.3 审计

| action | 时机 | payload 必含 |
| --- | --- | --- |
| `document.upload` | `register_document` 成功 | `kb_id`, `title`, `mime_type` |
| `document.delete` | 软删成功 | `kb_id`, `title` |
| `document.reingest` | 单条或批量 reingest | `kb_id` |
| `ingest.fail` | Worker 将文档标 `failed`（尽力而为，失败不阻断） | `kb_id`, `error_code` |

日志 Tab 过滤扩展：`payload.kb_id` 或 `target_id` 命中文档/库即可。

### 4.4 KB settings

`KnowledgeBaseUpdate.settings: dict | None`  
`KnowledgeBaseOut.settings: dict`  
`KnowledgeBaseOut` 增加只读 `effective_chunk_rules` / `effective_retrieval_rules`（resolve 结果），避免前端自己合并出错。

允许写入的键（其余 422）：

- `chunk_rules`: `max_tokens`, `min_tokens`, `overlap_tokens`, `clause_mode`, `keep_heading_prefix`
- `retrieval_rules`: `top_k`, `rerank_enabled`, `query_expand`

保存后 UI 文案：**已入库文档需重新解析后切块才会变化。**

### 4.5 查询理解

**指代消解**（仅 Chat，`_stream_answer`）：

- 条件：本会话已有 ≥1 条 completed 用户消息（当前轮之前）。
- 用 Chat LLM 非流式短调用：输入最近 4 条消息 + 当前问题，要求只输出改写后的独立问句，不要解释。
- 超时/空/异常 → 使用原 query。
- `rewritten_query` 写入检索结果与 SSE `retrieval` 事件（已有字段）。

**查询扩展**：

- `RetrievalRulesConfig.query_expand: bool = False`
- 触发：`query_expand` 为真，且（无命中 **或** 融合第一名 RRF 分低于内部常数 `EXPAND_RRF_FLOOR=0.016`，约等于两路都排很后）。
- LLM 生成 1 条改写，第二次 `search` 的向量+全文结果与第一次 RRF 合并后再截断。
- Playground：`options.query_expand: bool` 覆盖 Profile（仅本次请求）。

Fake LLM：指代/扩展提示命中时返回固定可断言字符串，避免测试打网。

## 5. 前端

| 面板 | 行为 |
| --- | --- |
| 文件列表 | 多选；批量删除/重试；启用开关；分块数列；元数据抽屉（按 `metadata_schema` 动态字段） |
| 检索测试 | Top-K / Rerank 默认取 effective 规则；可选「查询扩展」；展示 `rewritten_query` |
| 配置 | 切块/召回可编辑并 PATCH `settings`；改绑定模板清空或保留 settings（**保留**，浅合并仍以 KB 为准） |
| 日志 | 展示 document.* / ingest.fail |

禁用开关：`PERM_WRITE` 角色才可改；member 只读看到灰色开关。

## 6. 行业打磨（W4）

| 模板 | 变更 |
| --- | --- |
| `discrete_manufacturing` | `overlap_tokens`: 64 → **128**（与 04 文档一致）；词典保留并允许注释说明需客户语料扩展 |
| `process_industry` | 保持 `clause_mode`；`parse_rules.dictionary` 增加常见标准号碎片示例（如 `GB/T`、`AQ/T`） |
| golden | 新增 `backend/evals/golden.discrete.jsonl`、`golden.process.jsonl`（可用现有手册/合成条款）；CI **不**改阈值 |

种子刷新：`seed.py` 已对内置模板 refresh 规则，本地 `make seed` 即可。

## 7. 验收

1. 禁用文档后 Search/Chat 不命中；列表仍在，可再启用。
2. 批量 2 个失败件 reingest，状态离开 `failed`。
3. 日志出现 upload/delete。
4. KB A/B 同 Profile，A 改 `max_tokens` 后仅 A 的新 ingest 块大小变化。
5. 多轮「它的检修周期」检索 query ≠ 用户原句（非 Fake 环境）或 Fake 下等于测试夹具改写。
6. `pnpm lint && pnpm typecheck`；后端相关 pytest 绿；`make eval-ci` 仍过。

## 8. PR 切片

1. `feat/m6-w1-doc-ops` — enabled + batch + audit + 文件表  
2. `feat/m6-w2-kb-settings` — settings PATCH + 配置/检索 UI  
3. `feat/m6-w3-query-understand` — 指代 + 扩展  
4. `feat/m6-w4-profiles-eval` — seed + golden + 07-progress  
