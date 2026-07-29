# M2 检索与问答 — 设计说明

**日期**：2026-07-29  
**分支**：`feat/m2-retrieval`  
**状态**：待用户审阅规格  
**依据**：`docs/01`–`06`；用户确认范围 A / Fake 模型 / 租户内全部 KB

---

## 1. 目标与非目标

### 目标（可演示切片）

1. 对已入库知识库提问，经混合检索拿到证据，Fake LLM 流式生成带 `[n]` 的回答。
2. `POST /search` 可独立调试召回质量（分项 scores + 耗时）。
3. 会话 / 消息 / 引用持久化；前端 `/chat` 流式渲染 + 证据面板。
4. 拒答与引用编号校验按 04 文档落地（简化阈值可配置）。

### 非目标（明确延后）

| 项 | 延后至 |
| --- | --- |
| `kb_grants` 细粒度授权 | M4 |
| Cross-Encoder 重排常态化 | 配置开关默认关；真开依赖真实模型 |
| 查询改写 / 多轮指代消解 | M2 末可选；MVP 首轮不做 |
| pdf.js 引用高亮跳转 | M3 |
| 点赞点踩 / 重新生成 | M3 |
| 真实 Embedding / LLM | 环境变量已支持，M2 验收用 Fake |

---

## 2. 决策摘要

| 决策 | 选择 | 理由 |
| --- | --- | --- |
| 模块切分 | `retrieval` + `chat` | 符合 01 架构；检索可独立测 |
| 模型 | Fake Embedding + Fake LLM | 零外部依赖，CI 可绿 |
| KB 可见性 | 租户内未删除 KB | grants 留 M4 |
| 重排 | 默认关 | MVP 不依赖真实 Cross-Encoder |
| 上下文扩展 | 默认 `expand_context=1` | 同文档 `seq±1`；表格 chunk 不扩 |
| RRF | `k=60` | 与 04 文档一致 |
| 拒答阈值 | 空召回；或 top1 RRF 分数 &lt; `min_score_threshold`（默认 0.35，可配） | MVP 不做词汇重叠率（Fake 向量下噪声大） |

---

## 3. 模块边界

```
retrieval                          chat
─────────                          ────
混合召回 / RRF / expand            会话 CRUD
POST /search                       提示词组装
不调用 LLM                         SSE 编排 + 引用校验
                                   只通过 RetrievalService.search() 取证
```

跨模块：仅 service 调用，禁止 chat 直接 join `chunks`。

---

## 4. 数据模型（迁移 `0003`）

与 `docs/02` §4.7 对齐：

- `conversations`：`tenant_id`, `user_id`, `kb_ids uuid[]`, `title`, `deleted_at`, 时间戳
- `messages`：`role`, `content`, `status`(`streaming|completed|failed`), `retrieval_meta`, `token_usage`, `model`
- `citations`：`chunk_id`（无 FK）, `document_id`, `index_no`, `quote`, `page_start`, `bboxes`, `score`；`UNIQUE(message_id, index_no)`

三表均启用 RLS（`tenant_id = app_current_tenant()`），与 M1 一致。

索引：`messages(conversation_id, created_at)`；`citations(message_id)`。

---

## 5. 检索设计

### 5.1 输入归一

查询文本必须经 `ingestion.parsers.normalize.normalize`；全文查询 token 经 `ingestion.chunkers.tsv.build_tsv` 同口径，再 `to_tsquery('simple', ...)`（非法 token 过滤）。

### 5.2 双路召回（并行）

- **向量**：`ORDER BY embedding <=> :q`（cosine 距离），取 `top_n`（默认 50）；分数 `1 - distance`。
- **全文**：`tsv @@ query`，`ts_rank_cd`，取 `top_n`。
- SQL 前置过滤：`tenant_id`、`kb_id = ANY(:kb_ids)`、文档未软删。

`kb_ids` 缺省时 = 当前租户全部未删除知识库；若显式传入，须 ⊆ 租户可见集合，否则 404/校验失败。

### 5.3 融合与后处理

1. RRF：`score += 1/(60 + rank)`，rank 从 0 计。
2. 取 RRF Top-30。
3. `expand_context=n`：对非 `table` chunk 拉同文档 `seq±n`，去重后按文档+seq 拼证据（生成用 Top-5～8）。
4. 重排：若 `options.rerank=true` 且 Provider 可用则对 Top-30 重排；否则跳过。

### 5.4 `POST /search` 响应

每条结果含：`chunk_id`, `document_id`, `document_title`, `heading_path`, `content`, `page_start`, `page_end`, `bboxes`, `scores{vector,fulltext,rrf,rerank?}`；顶层 `stats{vector_ms,fulltext_ms,rerank_ms,total_ms}`。

---

## 6. 问答设计

### 6.1 流程

1. 解析/创建 `conversation_id`；写入 user message（`completed`）。
2. 创建 assistant message（`streaming`）；发 `message_created`。
3. 调 `RetrievalService.search`；发 `retrieval`。
4. 拒答？→ 发 `no_answer`，assistant 落库 `completed` + 拒答文案，结束（不调 LLM）。
5. 组装系统提示 + 编号证据 `[1]…[k]`；发 `citations`（含 quote/bboxes 快照）。
6. Fake/真实 LLM `stream`；逐片 `delta`；累积正文。
7. 校验 `[n]`：剔除越界；`used_citations` 仅实际出现编号；更新 assistant content/status/`token_usage`；发 `done`。
8. 客户端断开：取消上游生成；assistant `status=failed`，保留已生成部分。

### 6.2 提示词约束（MVP）

- 仅根据证据回答；事实后标 `[n]`。
- 数值/型号/标准号不得臆造或换算。
- 资料不足则明确说明缺什么（与拒答路径互补）。

### 6.3 Fake LLM 行为

现有 `FakeLLMProvider`：若 system 含 `[1]` 则回复模板 + `[1]`。M2 应保证提示词注入证据编号，便于引用校验与前端证据面板联调。

---

## 7. API 清单（MVP）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/search` | 纯检索 |
| GET/POST | `/conversations` | 列表 / 创建 |
| GET | `/conversations/{id}/messages` | 历史含 citations |
| DELETE | `/conversations/{id}` | 软删 |
| POST | `/chat/completions` | SSE 流式问答 |

不做：`POST /messages/{id}/feedback`（M3）。

---

## 8. 前端

- 新域：`frontend/src/features/chat/`（api / hooks / ChatPage + EvidencePanel）。
- 路由 `/chat` 替换占位；复用 `lib/sse.ts` 的 `streamEvents`。
- UI：左侧/主区消息流；右侧证据列表（点击高亮对应角标，**不**跳 PDF——M3）。
- 发问前可选一个或多个本租户 KB（默认全选或最近一个有文档的 KB）。

---

## 9. 测试与验收

### 自动化

- 单元：`rrf_fuse`；引用校验（越界剔除、`used_citations`）。
- API：登录后 `/search` 对种子/测试 KB 返回结构；`/chat/completions` SSE 事件顺序冒烟（Fake）。

### 手工验收

1. M1 已 `ready` 的手册所在 KB。
2. `/search` 可见合理命中与 scores。
3. 问答页提问 → 流式文字 → 证据面板有条目 → `done`。
4. 空 KB / 无关问题触发 `no_answer` 或低置信提示。

---

## 10. 文件落点（摘要）

见实施计划（`docs/superpowers/plans/`）；后端 `modules/retrieval/*`、`modules/chat/*`、迁移 `0003`；前端 `features/chat/*`；`api.py` 挂载。

---

## 11. 风险

| 风险 | 缓解 |
| --- | --- |
| Fake 向量与真实工业召回差异 | `/search` 分项 scores 便于日后换真实 Embedding 对比 |
| 扫描件 OCR 文本噪声导致拒答过多 | 阈值可配；验收优先用文本层 AQ4102 |
| SSE 与 DB 事务时长 | 检索与落库分阶段 commit；流式中定期 flush content |

---

## 12. 规格自检

- [x] 无 TBD 占位阻塞实现
- [x] 与 02/03/04 无冲突（拒答略简化已写明）
- [x] 范围与用户确认的 A/Fake/租户 KB 一致
- [x] 非目标已列出，避免范围膨胀
