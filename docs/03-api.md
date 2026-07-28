# 03 API 设计

## 1. 通用约定

| 项 | 约定 |
| --- | --- |
| 基础路径 | `/api/v1`，版本升级时并行提供 `/api/v2`，旧版本至少保留 6 个月 |
| 认证 | `Authorization: Bearer <access_token>`（JWT，30 分钟）+ Refresh Token（7 天，HttpOnly Cookie）；服务间调用用 `X-API-Key` |
| 租户上下文 | 从 JWT 的 `tid` 声明中解析；用户属于多租户时通过 `POST /auth/switch-tenant` 换取新 token，**不接受客户端传 tenant 参数** |
| 请求追踪 | 客户端可传 `X-Request-Id`，未传则服务端生成，全链路透传并在响应头回带 |
| 时间格式 | RFC 3339，UTC，如 `2026-07-28T07:15:30Z` |
| 命名 | 路径与字段一律 `snake_case`，资源名复数 |
| 分页 | 游标分页 `?cursor=<opaque>&limit=20`，响应含 `next_cursor`；仅管理后台的统计接口使用偏移分页 |
| 幂等 | 所有 `POST` 创建类接口接受 `Idempotency-Key` 头，24 小时内重复键返回首次结果 |
| 长任务 | 一律返回 `202 Accepted` + 任务标识，通过轮询或 SSE 获取进度 |

### 1.1 错误响应

统一结构，禁止裸返回字符串：

```json
{
  "error": {
    "code": "document_too_large",
    "message": "文件大小超过 100 MB 限制",
    "details": { "limit_bytes": 104857600, "actual_bytes": 137428992 },
    "request_id": "01J8XQ4Z7K9M2N3P4R5S6T7V8W"
  }
}
```

`code` 是稳定的机器可读标识，前端据此做分支；`message` 面向用户，可国际化，**前端不得对 message 做任何逻辑判断**。

| HTTP | 使用场景 |
| --- | --- |
| 400 | 参数校验失败（`validation_error`，details 中给出字段级错误） |
| 401 | 未认证或 token 过期（`unauthenticated` / `token_expired`） |
| 403 | 已认证但无权限（`forbidden`），**不泄露资源是否存在** |
| 404 | 资源不存在或当前租户不可见 |
| 409 | 状态冲突，如重复上传（`duplicate_document`）、并发修改 |
| 413 | 文件过大 |
| 422 | 语义错误，如知识库未就绪时发起问答 |
| 429 | 限流或配额耗尽（`rate_limited` / `quota_exceeded`，响应头带 `Retry-After`） |
| 503 | 上游模型服务不可用（`provider_unavailable`） |

对不存在与无权限的处理：**跨租户访问一律返回 404**（RLS 天然过滤，查不到即 404），租户内无权限返回 403。这样不会通过状态码暴露其他租户的资源存在性。

## 2. 端点清单

### 认证与身份

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/login` | 邮箱密码登录，返回 access/refresh token |
| POST | `/auth/refresh` | 刷新 access token |
| POST | `/auth/logout` | 注销，吊销 refresh token |
| POST | `/auth/switch-tenant` | 切换当前租户上下文 |
| GET | `/me` | 当前用户、所属租户列表、当前租户内角色 |

### 知识库

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/knowledge-bases` | 列出当前用户可见的知识库 |
| POST | `/knowledge-bases` | 创建，需指定 `profile_code` |
| GET | `/knowledge-bases/{kb_id}` | 详情，含文档数、chunk 数、就绪状态 |
| PATCH | `/knowledge-bases/{kb_id}` | 更新名称、描述、局部配置 |
| DELETE | `/knowledge-bases/{kb_id}` | 软删除，级联标记文档 |
| GET | `/knowledge-bases/{kb_id}/grants` | 授权列表 |
| PUT | `/knowledge-bases/{kb_id}/grants/{user_id}` | 授予/变更权限 |
| DELETE | `/knowledge-bases/{kb_id}/grants/{user_id}` | 撤销权限 |

### 文档

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/knowledge-bases/{kb_id}/documents/upload-url` | 申请预签名直传 URL（大文件路径） |
| POST | `/knowledge-bases/{kb_id}/documents` | 登记文档并触发摄取（小文件可直接 multipart） |
| GET | `/knowledge-bases/{kb_id}/documents` | 列表，支持 `status`、`q`、`metadata.*` 过滤 |
| GET | `/documents/{doc_id}` | 详情，含摄取进度与错误信息 |
| DELETE | `/documents/{doc_id}` | 软删除并清理 chunks |
| POST | `/documents/{doc_id}/reingest` | 重新摄取，可指定起始阶段 |
| GET | `/documents/{doc_id}/preview-url` | 原文预签名下载 URL（15 分钟有效） |
| GET | `/documents/{doc_id}/chunks` | 分块列表，用于质量排查 |
| GET | `/documents/{doc_id}/events` | SSE，实时推送摄取进度 |

### 检索与问答

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/search` | 纯检索，不生成。用于调试与"仅查资料"场景 |
| POST | `/chat/completions` | 流式问答（SSE） |
| GET | `/conversations` | 会话列表 |
| POST | `/conversations` | 创建会话 |
| GET | `/conversations/{id}/messages` | 历史消息（含引用） |
| DELETE | `/conversations/{id}` | 删除会话 |
| POST | `/messages/{id}/feedback` | 点赞/点踩 + 原因，沉淀为评测样本 |

### 行业配置与管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/industry-profiles` | 内置模板 + 本租户自定义 |
| POST | `/industry-profiles` | 基于内置模板派生自定义配置 |
| PATCH | `/industry-profiles/{id}` | 更新，写入前做 schema 校验 |
| GET | `/admin/audit-logs` | 审计日志查询 |
| GET | `/healthz` `/readyz` | 存活与就绪探针，不需认证 |

### 大模型接入管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/model-connections` | 接入点列表（平台级只读 + 本租户自建），凭证掩码返回 |
| POST | `/model-connections` | 新建接入点 |
| PATCH | `/model-connections/{id}` | 更新配置；改动递增 `version` 使 Provider 缓存失效 |
| PUT | `/model-connections/{id}/credential` | 单独更新凭证，**只写不读** |
| POST | `/model-connections/{id}/test` | 连通性探测，实调一次最小请求并返回延迟 |
| DELETE | `/model-connections/{id}` | 删除；历史用量保留 |
| GET | `/model-connections/routes` | 当前各用途实际命中的接入点，用于排查"为什么用的不是我配的那个" |
| GET | `/usages/summary` | 概览卡片：本期 token、成本、调用数、成功率及环比 |
| GET | `/usages/series` | 时间序列，供趋势类图表使用 |
| GET | `/usages/breakdown` | 维度分布，供环形图与排行榜使用 |
| GET | `/usages/records` | 用量明细，支持导出 CSV |

## 3. 关键接口详设

### 3.1 文档上传

小于 20 MB 走直接上传，大文件走预签名直传以避免占用应用进程的内存与连接。

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/upload-url
Content-Type: application/json

{ "filename": "液压站操作手册.pdf", "file_size": 48123904, "mime_type": "application/pdf" }
```

```json
{
  "upload_url": "https://oss.example.com/...&X-Amz-Signature=...",
  "storage_key": "t/{tenant}/kb/{kb_id}/2026/07/01J8X....pdf",
  "expires_at": "2026-07-28T07:30:00Z"
}
```

客户端 PUT 到 `upload_url` 后登记：

```http
POST /api/v1/knowledge-bases/{kb_id}/documents
Idempotency-Key: 8f14e45f-...

{
  "storage_key": "t/{tenant}/kb/{kb_id}/2026/07/01J8X....pdf",
  "title": "液压站操作手册",
  "checksum": "sha256:9f86d0...",
  "metadata": { "equipment_code": "HYD-2201", "revision": "C", "effective_date": "2026-03-01" }
}
```

`metadata` 按该知识库所属 profile 的 `metadata_schema` 校验，未定义的字段直接拒绝而非静默丢弃——工业场景的元数据往往用于后续的过滤检索，静默丢弃会造成难以排查的召回缺失。

响应 `202`：

```json
{ "document_id": "01J8X...", "status": "pending", "job_id": "01J8Y..." }
```

### 3.2 摄取进度（SSE）

```http
GET /api/v1/documents/{doc_id}/events
Accept: text/event-stream
```

```
event: progress
data: {"stage":"parsing","progress":0.35,"page_done":42,"page_total":120}

event: progress
data: {"stage":"embedding","progress":0.80,"chunk_done":240,"chunk_total":300}

event: completed
data: {"status":"ready","chunk_count":300,"duration_ms":73210}
```

失败时：

```
event: failed
data: {"status":"failed","error_code":"ocr_timeout","error_detail":"page 88 exceeded 60s","retryable":true}
```

前端在列表页用 TanStack Query 轮询（3 秒间隔，`ready`/`failed` 后停止），仅在详情页使用 SSE。理由是列表页同时打开几十个 SSE 连接会耗尽浏览器的并发连接数，而轮询在这个场景下足够。

### 3.3 检索

```http
POST /api/v1/search
{
  "query": "液压站压力异常报警怎么处理",
  "kb_ids": ["01J8A..."],
  "top_k": 10,
  "filters": { "metadata.equipment_code": "HYD-2201" },
  "options": { "rerank": true, "expand_context": 1 }
}
```

```json
{
  "results": [
    {
      "chunk_id": "01J8Z...",
      "document_id": "01J8X...",
      "document_title": "液压站操作手册",
      "heading_path": ["4 故障处理", "4.3 压力异常"],
      "content": "当系统压力超过 16 MPa 时，溢流阀应……",
      "page_start": 57,
      "page_end": 57,
      "bboxes": [{ "page": 57, "bbox": [72.0, 310.5, 523.0, 402.1] }],
      "scores": { "vector": 0.842, "fulltext": 0.611, "rrf": 0.0317, "rerank": 0.958 }
    }
  ],
  "stats": { "vector_ms": 41, "fulltext_ms": 18, "rerank_ms": 132, "total_ms": 196 }
}
```

`scores` 全量返回各阶段分数是刻意的：调参和排查召回问题时，只有 rerank 后的最终分是不够的，需要看到融合前的原始信号。这个字段在生产环境也不隐藏，它对最终用户无害，对运维极有价值。

### 3.4 问答（SSE）

```http
POST /api/v1/chat/completions
{
  "conversation_id": "01J9A...",
  "kb_ids": ["01J8A..."],
  "message": "液压站压力异常报警怎么处理？",
  "options": { "temperature": 0.1, "stream": true }
}
```

事件序列，顺序有语义：

```
event: message_created
data: {"message_id":"01J9B...","conversation_id":"01J9A..."}

event: retrieval
data: {"rewritten_query":"液压站 压力异常 报警 处理 步骤","hit_count":8,"took_ms":196}

event: citations
data: {"citations":[{"index_no":1,"document_id":"01J8X...","document_title":"液压站操作手册","page_start":57,"bboxes":[...],"quote":"当系统压力超过 16 MPa 时……"}]}

event: delta
data: {"text":"当液压站出现压力异常报警时，按以下步骤处理："}

event: delta
data: {"text":"\n\n1. 立即确认系统压力表读数是否超过 16 MPa [1]。"}

event: done
data: {"message_id":"01J9B...","finish_reason":"stop","used_citations":[1,3],"usage":{"prompt_tokens":3241,"completion_tokens":412},"took_ms":4821}
```

设计要点：

- `citations` 早于 `delta` 下发，前端可在生成开始前就渲染证据面板，显著改善等待体感。
- `done` 中的 `used_citations` 是**服务端从正文里解析出的实际被引用编号**，前端据此把未被引用的证据置灰或折叠。模型经常会拿到 8 条证据只用其中 3 条，全部高亮展示反而降低可信度。
- 客户端断开时服务端必须终止上游 LLM 调用（FastAPI 中通过 `request.is_disconnected()` 或 `anyio` 取消作用域），否则会持续烧 token。这是流式接口最容易被忽略的成本泄漏点。
- 生成中断（网络异常）时消息以 `status='failed'` 落库并保留已生成部分，前端提供"重新生成"。

### 3.5 拒答的表达

当检索无有效证据时，不走 LLM，直接返回结构化拒答：

```
event: no_answer
data: {"reason":"no_relevant_evidence","suggestions":["尝试补充设备型号","确认该资料是否已上传到当前知识库"]}
```

用独立事件而非让模型生成一段"抱歉我不知道"，理由有三：省一次 LLM 调用；文案可控可运营；前端可以针对性地引导用户补充信息或跳转上传，把死路变成入口。

### 3.6 用量图表接口

仪表盘上有七张图，但**不设计七个接口**。所有图表共享同一套筛选条件，拆成三类语义清晰的接口，前端按维度组合渲染。

#### 时间序列（趋势类图表）

```http
GET /api/v1/usages/series
    ?from=2026-07-01T00:00:00Z&to=2026-07-28T23:59:59Z
    &granularity=day&timezone=Asia/Shanghai
    &metrics=prompt_tokens,completion_tokens,cost,call_count,success_rate
    &group_by=purpose
    &models=gpt-x,bge-m3
```

```json
{
  "granularity": "day",
  "timezone": "Asia/Shanghai",
  "series": [
    {
      "group": { "purpose": "chat" },
      "points": [
        { "t": "2026-07-27", "prompt_tokens": 412300, "completion_tokens": 58120,
          "cost": 1.842, "call_count": 731, "success_rate": 0.995 }
      ]
    },
    { "group": { "purpose": "embedding" }, "points": [ ... ] }
  ],
  "currency": "USD",
  "stale_until": "2026-07-28T09:00:00Z"
}
```

设计要点：

- **`timezone` 是必填参数**。服务端读取 UTC 小时桶后按该时区重组成天，前端不做任何时间聚合。把时区换算放在前端是这类功能最常见的 bug 来源——夏令时和跨日边界几乎必错。
- **`granularity` 由前端根据时间跨度决定**（≤48 小时用 `hour`，否则 `day`），但服务端会校验：跨度超过 7 天时拒绝 `hour` 粒度并返回 400，防止一次请求拉回上千个点把图表压垮。
- **`group_by` 只允许 `purpose` / `model` / `connection_id` 三选一**。多维交叉的诉求用两次请求解决，不支持任意维度组合——那会让预聚合表的查询计划失控。
- **`stale_until` 显式告知数据新鲜度**。预聚合最长有 1 小时延迟，前端据此在图表角落标注"数据截至 17:00"，避免用户以为是实时的然后困惑于"我刚问了怎么没涨"。

#### 维度分布（环形图与排行榜）

```http
GET /api/v1/usages/breakdown?from=...&to=...&dimension=model&metric=cost&top=10
```

```json
{
  "items": [
    { "key": "gpt-x", "label": "gpt-x", "value": 42.31, "share": 0.78, "call_count": 12043 },
    { "key": "bge-m3", "label": "bge-m3", "value": 8.02, "share": 0.15, "call_count": 91220 }
  ],
  "others": { "value": 3.77, "share": 0.07 },
  "total": 54.10
}
```

`dimension` 支持 `model` / `purpose` / `connection` / `user` / `knowledge_base`。超出 `top` 的部分统一归入 `others`，由服务端合并，前端不需要自己截断——否则各图表的"其他"口径会不一致。

#### 概览卡片

```http
GET /api/v1/usages/summary?period=month&timezone=Asia/Shanghai
```

```json
{
  "period": { "from": "2026-07-01", "to": "2026-07-28" },
  "total_tokens": 18421093, "total_cost": 54.10, "call_count": 103263,
  "success_rate": 0.9931,
  "quota": { "token_limit": 30000000, "used_ratio": 0.614, "reset_at": "2026-08-01T00:00:00+08:00" },
  "compare_previous": { "total_tokens": 0.23, "total_cost": 0.19 }
}
```

`compare_previous` 是环比变化率而非上期绝对值，前端直接渲染成 `+23%` 的角标，不做除法。**任何需要前端计算的派生指标都应该由服务端算好**，否则同一个数字在不同页面会因为四舍五入或口径差异而不一致。

#### 接入点测试

```http
POST /api/v1/model-connections/{id}/test
```

```json
{
  "ok": true,
  "latency_ms": 412,
  "model_echo": "gpt-x-2026-05",
  "checked_at": "2026-07-28T08:12:03Z"
}
```

失败时返回 200 而非 5xx，body 中 `ok: false` 并给出 `error_code`（`auth_failed` / `model_not_found` / `timeout` / `network_error`）与原始错误摘要。这是一个诊断接口，"探测本身成功执行了但目标不通"是正常结果，不是服务端错误——用 5xx 表达会让前端难以区分是探测挂了还是目标挂了。

## 4. 前端页面与接口映射

| 页面 | 主要接口 | 交互要点 |
| --- | --- | --- |
| 登录 / 租户切换 | `/auth/*`、`/me` | 多租户用户登录后强制选择租户 |
| 知识库列表 | `GET /knowledge-bases` | 展示就绪文档数与处理中数量 |
| 文档管理 | `documents` 相关 | 拖拽批量上传；处理中项轮询；失败项一键重试并展示错误原因 |
| 文档详情 | `preview-url`、`chunks`、`events` | 左侧 pdf.js 预览，右侧分块列表，点击分块在原文高亮——这是排查召回问题最有效的工具 |
| 问答 | `chat/completions`、`conversations` | 正文中的 `[n]` 渲染为可点击角标，点击右侧定位到证据并在预览中高亮 |
| 检索调试台 | `POST /search` | 面向管理员，可调 top_k、开关重排、对比各阶段分数 |
| 行业配置 | `industry-profiles` | 表单化编辑 jsonb，提供 JSON 与表单双视图 |
| 模型接入管理 | `model-connections` 相关 | 接入点卡片列表，含健康状态灯与"测试连接"按钮；凭证输入框只写不回显；`routes` 视图展示各用途当前实际命中的接入点 |
| 用量仪表盘 | `/usages/summary`、`/series`、`/breakdown` | 顶部概览卡片 + 七张 Recharts 图表；共享时间与维度筛选器，切换筛选只重取受影响的接口 |

### 4.1 前端目录结构

```
src/
  app/            路由、Provider、全局布局
  features/       按业务域切分，与后端模块一一对应
    auth/  knowledge/  documents/  chat/  profiles/  modelops/  admin/
      api.ts        该域的接口调用与类型（由 OpenAPI 生成的类型再包一层）
      hooks.ts      TanStack Query hooks
      components/   仅本域使用的组件
  components/ui/  shadcn 基础组件
  lib/            sse.ts / http.ts / format.ts
  types/          openapi.gen.ts（自动生成，禁止手改）
```

类型来源单一：后端 FastAPI 导出 OpenAPI，前端用 `openapi-typescript` 生成 `openapi.gen.ts`，纳入 CI 校验。接口一改，前端编译即报错，避免线上才发现字段对不上。

## 5. 限流与配额

| 维度 | 默认限制 | 实现 |
| --- | --- | --- |
| 单用户问答 | 20 次/分钟 | Redis 滑动窗口 |
| 单租户并发问答 | 10 | Redis 信号量，超出返回 429 |
| 单租户月度 token | 由 `tenants.quota` 定义 | 查询 `llm_usages` 聚合，缓存 5 分钟 |
| 上传文件 | 单文件 100 MB，单租户日 500 个 | 应用层校验 |

配额耗尽返回 429 而非 403，并在 `details` 中给出当前用量与重置时间，让前端能准确提示"本月额度已用完，8 月 1 日重置"。

---

上一篇：[02 数据模型](./02-data-model.md) ｜ 下一篇：[04 RAG 流水线](./04-rag-pipeline.md)
