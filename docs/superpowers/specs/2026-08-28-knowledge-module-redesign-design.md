# 知识库模块功能与设计书（对照参考 UI 重设计）

> 状态：实施中  
> 日期：2026-08-28  
> 参考：RAG 平台类控制台（文件列表 / 检索测试 / 日志 / 配置 四 Tab 工作台）

## 1. 目标

将当前「单页 KB 详情」重构为 **知识库工作台**：左侧上下文导航 + 右侧功能面板，对齐参考截图的信息架构，并映射到本平台已有后端能力（Industry Profile、摄取流水线、`POST /search`、审计日志）。

**非目标（本阶段不做）：**

- 知识图谱 / RAPTOR / 实体类型抽取
- 外部数据源链接（S3 目录同步等）
- 单文档启用/禁用开关（需新字段与检索过滤）
- KB 级 `settings` JSON 在线编辑（仍通过行业模板 + Admin Profiles 管理）

---

## 2. 参考 UI 功能梳理

### 2.1 工作台壳层

| 区域 | 参考功能 | 本平台映射 |
| --- | --- | --- |
| 侧栏头部 | 库名、文件数、容量、创建时间 | `KnowledgeBaseOut`：name、doc_count、chunk_count、created_at |
| 文件列表 | 文档 CRUD、批量上传、解析状态 | 已有 upload / list / reingest / delete |
| 检索测试 | 调参 + 即时召回结果 | `POST /api/v1/search`，kb_ids 限定当前库 |
| 日志 | 操作与任务记录 | 租户审计 `GET /admin/audit-logs`，按 kb_id 过滤 grant/删库 |
| 配置 | 基本信息、切块、嵌入、召回 | 基本信息 PATCH；切块/检索 → Industry Profile |

### 2.2 文件列表（参考图 5–6）

| 列/能力 | 参考 | 本平台 |
| --- | --- | --- |
| 名称 | ✓ | title + 链到文档详情 |
| 上传日期 | ✓ | created_at |
| 分块数 | ✓ | 文档级暂无，列表不展示（详情页 chunks） |
| 解析/状态 | Parse + Success/Failed | pending/parsing/…/ready/failed + SSE 进度 |
| 批量选择 | ✓ | 后置：批量删除/重试 |
| 启用开关 | ✓ | **不做**（无 disabled 字段） |
| 统计卡片 | 总数 / 下载中 / 处理中 | 总数 / 摄取中 / 失败 |

### 2.3 检索测试（参考图 4）

| 参数 | 参考 | 本平台 API |
| --- | --- | --- |
| 相似度阈值 | slider | **暂无**（RRF 分数，非 0–1 阈值） |
| 向量/全文权重 | 双 slider | **暂无**（RRF 固定融合） |
| Rerank 模型 | 下拉 | `options.rerank` boolean |
| Top-K | 下拉 | `top_k` |
| 知识图谱 | 开关 | **不做** |
| 查询框 + 运行 | ✓ | SearchRequest.query |
| 结果列表 | chunk + 分数 | SearchHitOut |

### 2.4 配置（参考图 1–3）

| 配置项 | 参考 | 本平台 |
| --- | --- | --- |
| 名称 / 描述 | ✓ | PATCH `/knowledge-bases/{id}` |
| 语言 / 头像 | ✓ | **不做** |
| 嵌入模型 | 下拉 | 只读展示 `embedding_model`（租户级连接） |
| 召回条数 top_k | slider | 只读：Profile `retrieval_rules.top_k` |
| 切块大小 / overlap | slider | 只读：Profile `chunk_rules` |
| PDF 解析器 / PageIndex | 下拉/开关 | 固定管线（PDF 文本层+OCR），Profile 无此项 |
| 行业模板 | 类似「内置 General」 | `profile_code` 改绑 |
| 成员授权 | — | KbGrantsPanel |
| 数据源 / 图谱 / RAPTOR | ✓ | **标注「路线图」** |

---

## 3. 信息架构（新）

```
/knowledge                          知识库列表
/knowledge/:kbId                    → 重定向 /files
/knowledge/:kbId/files              文件列表（默认）
/knowledge/:kbId/retrieval          检索测试
/knowledge/:kbId/logs               日志
/knowledge/:kbId/settings           配置
/knowledge/:kbId/documents/:docId   文档详情（不变）
```

### 3.1 布局线框

```
┌─────────────────────────────────────────────────────────────┐
│ [全局 App 侧栏] │ KB 工作台                                    │
│                 │ ┌──────────┬──────────────────────────────┐ │
│                 │ │ KB 侧栏   │ 面板标题 + 内容               │ │
│                 │ │ 库名/统计 │                              │ │
│                 │ │ 文件列表  │                              │ │
│                 │ │ 检索测试  │                              │ │
│                 │ │ 日志      │                              │ │
│                 │ │ 配置      │                              │ │
│                 │ └──────────┴──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 组件拆分

| 组件 | 职责 |
| --- | --- |
| `KnowledgePage` | 库列表 + 新建 |
| `KbWorkspaceLayout` | KB 侧栏 + `<Outlet />` |
| `KbFilesPanel` | 统计、搜索、上传、文档表 |
| `KbRetrievalPanel` | 检索 playground |
| `KbLogsPanel` | KB 相关审计 |
| `KbSettingsPanel` | 基本信息、模板、只读规则、授权 |
| `DocumentDetailPage` | 预览 + 分块（不变） |

---

## 5. API 依赖

| 面板 | 端点 |
| --- | --- |
| 文件 | GET/POST documents, reingest, delete |
| 检索 | POST `/search` `{ query, kb_ids: [kbId], top_k, options: { rerank } }` |
| 日志 | GET `/admin/audit-logs` + 客户端按 payload.kb_id / target_id 过滤 |
| 配置 | PATCH KB, GET industry-profiles, grants CRUD |

---

## 6. 视觉

- 延续 DeepSeek 浅色壳层：Indigo 激活态 + Slate 文本
- KB 内侧栏：`w-52`，`border-r border-slate-200`
- 面板内 `panel` 卡片与用量/运营页一致

---

## 7. 验收标准

1. 从列表进入 KB → 默认文件 Tab，侧栏四入口可切换
2. 多文件上传、解析状态轮询、失败重试/删除可用
3. 检索测试对当前库 POST search，右侧展示 hit 与分数
4. 配置页可改名称/描述、改绑模板，展示只读 chunk/retrieval 规则
5. 日志页展示与本 KB 相关的 grant 与删库审计（admin/owner）
6. `pnpm lint && pnpm typecheck` 通过

---

## 8. 后续演进

- KB 级 `settings` PATCH，覆盖 chunk/retrieval 而不改全局 Profile
- 文档级 enable 开关 + 检索过滤
- 摄取/删除写审计
- 向量/全文权重与相似度阈值（检索引擎扩展）
- 批量文档操作
