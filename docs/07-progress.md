# 07 进展与计划

记录已完成的工作、由实测得出的结论，以及下一步的具体任务。每次推进后在此追加，不覆盖历史。

## 当前状态

| 项 | 值 |
| --- | --- |
| 阶段 | **M4 切片：运营 UI**（分支 `feat/m4-ops-ui`） |
| 下一里程碑 | QPS/并发限流；CI 债务；M5 |
| 代码量 | `/admin` 三 Tab：接入点 / 成员 / 审计 |
| 阻塞项 | 无 |

---

## 2026-08-04（M4 · 运营 UI）

### 完成内容

| # | 任务 | 状态 |
| --- | --- | --- |
| O-1 | 规格 / 计划 | ✓ |
| O-2 | `api.put` + worker F401 修复 | ✓ |
| O-3 | 接入点面板（CRUD / 凭证 / test / routes） | ✓ |
| O-4 | 成员 + 审计面板 | ✓ |
| O-5 | `/admin` 导航与 `/modelops` 重定向 | ✓ |

**决策**：单入口 Tab；平台接入点只读；不含 KB grants UI。

---

## 2026-08-04（M4 · 用量仪表盘）

### 完成内容

| # | 任务 | 状态 |
| --- | --- | --- |
| D-1 | 规格 / 计划 | ✓ |
| D-2 | series `latency_p95_ms`；breakdown `user`/`knowledge_base` | ✓ |
| D-3 | OpenAPI 同步 + `features/usages` | ✓ |
| D-4 | 七图仪表盘 + admin 导航 | ✓ |

**决策**：客户演示级；user/kb 走明细聚合；熔断标注不做；运营 UI 下一刀。

---

## 2026-08-04（M4 · 配额 429）

### 完成内容

| # | 任务 | 状态 |
| --- | --- | --- |
| Q-1 | 规格 / 计划 | ✓ |
| Q-2 | `QuotaExceeded` + `Retry-After` | ✓ |
| Q-3 | `QuotaService`（hourlies + Redis 5min） | ✓ |
| Q-4 | chat / search 挂载 `require_token_quota` | ✓ |
| Q-5 | 集成测试 | ✓ |

**决策**：仅 `monthly_tokens`；`limit≤0` 不限额；错误码 `quota_exceeded`。

---

## 2026-07-30（M4 · health 故障转移）

### 完成内容

| # | 任务 | 状态 |
| --- | --- | --- |
| H-1 | 规格 / 计划 | ✓ |
| H-2 | `probe_connection` 共用探针 | ✓ |
| H-3 | `/test` 失败写 `down` | ✓ |
| H-4 | `ProviderFactory` 跳过 `down`，全 down → env | ✓ |
| H-5 | Celery `modelops.probe_connections`（300s） | ✓ |
| H-6 | 集成测试 | ✓ |

**决策**：仅定时探测改 health；路由只跳过 `down`；不写 `degraded`；无前端。

---

## 2026-07-30（M4 · 用量埋点）

### 完成内容

| # | 任务 | 状态 |
| --- | --- | --- |
| U-1 | 规格 | ✓ |
| U-2 | 迁移 `0007`：pricing / usages / hourlies + RLS | ✓ |
| U-3 | `UsageRecorder` → Redis；Celery flush + hourlies | ✓ |
| U-4 | chat / retrieval / ingestion 埋点 | ✓ |
| U-5 | `GET /usages/summary|series|breakdown`（admin+） | ✓ |
| U-6 | seed 占位定价 + 测试 | ✓ |

**决策**：方案 1 扩展 modelops；Redis 缓冲；成本写入快照；本切片无前端、无配额 429、usages 不分区。

---

## 2026-07-30（M4 · 模型接入点）

### 完成内容

| # | 任务 | 状态 |
| --- | --- | --- |
| C-1 | 规格 / 计划 | ✓ |
| C-2 | 迁移 `0006` + Fernet 凭证 | ✓ |
| C-3 | `/model-connections` CRUD / test / routes | ✓ |
| C-4 | `ProviderFactory` 租户→平台→env | ✓ |
| C-5 | chat / retrieval / ingestion 接线 | ✓ |
| C-6 | seed 平台接入点 | ✓ |

**决策**：凭证应用层加密；本切片不做 health 故障转移与用量。

---

## 2026-07-29（M4 · 成员管理 + 审计）

### 完成内容

| # | 任务 | 状态 |
| --- | --- | --- |
| A-1 | 规格 / 计划 | ✓ |
| A-2 | 迁移 `0005_audit_logs` + RLS | ✓ |
| A-3 | `AuditService.record` + `GET /admin/audit-logs` | ✓ |
| A-4 | `/memberships` CRUD（admin+，邮箱加人） | ✓ |
| A-5 | 钩子：成员 / grant / 删 KB / login / switch-tenant | ✓ |
| A-6 | 集成测试 | ✓ |

**决策**：加人仅限已存在用户；审计写入失败不阻断主业务；admin 不可改/删 owner。

---

## 2026-07-29（M4 · kb_grants）

### 完成内容

| # | 任务 | 状态 |
| --- | --- | --- |
| G-1 | `KbGrant` ORM + `identity.permissions.visible_kb_ids` | ✓ |
| G-2 | KB list/get/写操作按权限收窄；同租户无权 403 | ✓ |
| G-3 | grants CRUD API | ✓ |
| G-4 | search/chat 走同一可见集 | ✓ |
| G-5 | 跨租户 / private / 授撤权 / owner 绕过测试 | ✓ |

**决策**：owner/admin 对本租户全部 KB 视为 manage；`manage` ⊃ `write` ⊃ `read`。

---

## 2026-07-29（M3 引用溯源）

### 完成内容（进行中 → 代码已落地）

| # | 任务 | 状态 |
| --- | --- | --- |
| M3-1 | 规格 / 计划 | ✓ |
| M3-2 | `GET /documents/{id}/chunks` | ✓ |
| M3-3 | 迁移 `0004` + `POST /messages/{id}/feedback` | ✓ |
| M3-4 | `MessageOut`：`document_title` / `used_citations` / `feedback` | ✓ |
| M3-5 | 共享 `PdfHighlightViewer`（react-pdf） | ✓ |
| M3-6 | 问答右栏列表⇄PDF + 赞踩 + used 置灰 | ✓ |
| M3-7 | 文档详情双栏 + 列表入口 | ✓ |

**范围**：标准 M3 核心（方案 A）；不做重新生成 / XLSX·PPTX·MD 解析。

**本地**：`make migrate` 后起 api/web；点 `[n]` 看右栏高亮；知识库文档标题进详情。

---

## 2026-07-29（真实 Embedding / LLM / Rerank）

### 完成内容

| # | 任务 | 状态 |
| --- | --- | --- |
| P-1 | Settings：LLM / Embedding / Rerank 独立 base_url、api_key | ✓ |
| P-2 | Embedding：`dimensions=1024`，`batch_size≤10`（DashScope） | ✓ |
| P-3 | Rerank：`compatible-api` + `/reranks` + `qwen3-rerank`；检索默认开 | ✓ |
| P-4 | AQ4102 文档 reingest（真实向量）→ `ready` | ✓ ~10s |
| P-5 | `scripts/compare_retrieval.py`：RRF vs RRF+rerank 报告 | ✓ |
| P-6 | DeepSeek `deepseek-v4-flash` SSE 问答 → `done` | ✓ |

**配置要点**（本地 `.env`，勿提交）：

- LLM：`https://api.deepseek.com/v1`，模型须为 `deepseek-v4-flash` 或 `deepseek-v4-pro`（裸名 `deepseek-v4` 会 400）
- Embedding：`compatible-mode` + `text-embedding-v4`
- Rerank：`compatible-api`（**不是** `compatible-mode`）+ `/reranks`

**对比摘录（AQ4102 KB）**：相关问「烟花爆竹流向登记」Top5 重叠 5/5，rerank 调整次序且 `scores.rerank≈0.94`；无关问「液压泵保养」重叠仅 2/5，重排改变候选集。报告目录：`backend/artifacts/retrieval-compare/`（gitignore）。

**说明**：reingest 后 Fake 向量已被覆盖，本次报告为 **真实向量下 RRF vs RRF+rerank**；若需 Fake vs Real，须另建 KB 或先落 Fake 快照再切模型。

**下一步**：合并本分支；密钥曾出现在聊天中，建议在控制台轮换。

---

## 2026-07-29（M2 检索与问答）

### 完成内容

| # | 任务 | 状态 |
| --- | --- | --- |
| M2-1 | 迁移 `0003`：conversations / messages / citations + RLS + ORM | ✓ |
| M2-2 | `rrf_fuse` + `validate_citations` 纯函数与单测 | ✓ |
| M2-3 | RetrievalService：normalize + 向量/全文 + RRF + expand；`POST /search` | ✓ |
| M2-4 | Chat SSE：`message_created`→`retrieval`→`citations`/`delta`/`done` 或 `no_answer`；会话 API | ✓ |
| M2-5 | 前端 `/chat`：多 KB 选择、流式渲染、证据面板 | ✓ |
| M2-验收·检索 | AQ4102 KB：`/search` 命中 5 条，含 `scores.rrf` / `vector` / `fulltext` | ✓ |
| M2-验收·问答 | 同 KB SSE：`message_created`…`citations`…`delta*`…`done` | ✓ |

**决策落地**：Fake Embedding + Fake LLM；KB 可见性 = 租户内未删除库（`kb_grants` 留 M4）；拒答阈值对照**向量相似度**（RRF 量纲不适合 0.35）。

**实现注意**：SSE 中途 `commit` 会结束事务并清掉 `SET LOCAL` 的 RLS 变量，需在 commit 后重写 `app.tenant_id` / `app.user_id`。

**本地联调**：

```bash
make migrate
make api && make web   # 已有 ready 文档即可
# 登录 → 问答 → 选知识库提问；或 curl /search 与 /chat/completions
```

**下一步**：合并 `feat/m2-retrieval`；M3 做 pdf.js 引用跳转与反馈；可选换真实 Embedding/LLM 对比召回。

---

## 2026-07-29（M1 收尾）

### 完成内容：M1 摄取链路

| # | 任务 | 状态 |
| --- | --- | --- |
| M1-1 | 知识库 / 文档 CRUD + 预签名 + multipart 上传 | ✓ |
| M1-2 | Celery 双队列 parse / embed + 状态机 | ✓ |
| M1-3 | PDF 文本层解析 + OCR 回退 + normalize / layout | ✓（`uv sync --extra ocr`；Intel Mac 钉住 onnxruntime&lt;1.24） |
| M1-4 | 结构感知分块 + `clause_mode` | ✓ |
| M1-5 | Embedding 写入 + HNSW（Fake Provider） | ✓ |
| M1-6 | 前端：知识库列表、拖拽上传、进度轮询、失败重试 | ✓ |
| M1-验收·文本层 | AQ4102（17 页）→ `ready`，约 8s，12 chunks | ✓ |
| M1-验收·扫描件 | OCR 依赖修复后对失败文档重试 | ✓ AQ3072（8 页扫描）parse≈108s → `ready` |

**已知遗留（不阻塞 M2）**：DOCX 解析、SSE 进度（现为轮询）、页级 Celery 并行（R1c）、100 页手册性能压测。

**下一步**：开 `feat/m2-retrieval`——向量 + 全文 + RRF、`POST /search`、流式问答 SSE。

---

## 2026-07-29（续）

### 进行中：M1 摄取链路

| # | 任务 | 状态 |
| --- | --- | --- |
| M1-1 | 知识库 / 文档 CRUD + 预签名 + multipart 上传 | ✓ |
| M1-2 | Celery 双队列 parse / embed + 状态机 | ✓ |
| M1-3 | PDF 文本层解析 + OCR 回退 + normalize / layout | ✓（OCR 为可选 extra） |
| M1-4 | 结构感知分块 + `clause_mode` | ✓ |
| M1-5 | Embedding 写入 + HNSW（Fake Provider） | ✓ |
| M1-6 | 前端：知识库列表、拖拽上传、进度轮询、失败重试 | ✓ |
| M1-验收 | 真实手册端到端 `ready` | ✓ AQ4102（17 页文本层）约 8s → ready，12 chunks |

**本地联调**：

```bash
make migrate && make seed
make api          # 终端 1
make worker       # 终端 2（必须能看到 ingest.parse_document / ingest.embed_document）
make web          # 终端 3
# 登录 → 知识库 → 上传 PDF → 状态变为 ready
```

**验收摘录（2026-07-29）**：`AQ4102-2026烟花爆竹流向登记通用规范.pdf` 经 multipart 上传后 `ready`，`page_count=17`，抽查 chunk 含文档标题前缀与页码区间。修复：`worker.py` 需显式导入 `app.modules.ingestion.tasks`，否则 Celery 丢弃未注册任务。

---

## 2026-07-29

### 完成内容：M0 工程骨架

对照 06 / 07 文档的 M0 验收标准落地，并补齐此前未入库的缺口。

| 任务 | 状态 | 产出 |
| --- | --- | --- |
| M0-1 monorepo | ✓ | `backend/` + `frontend/` + `deploy/` + `Makefile` |
| M0-2 Compose | ✓ | Postgres 16 + pgvector / Redis / MinIO |
| M0-3 FastAPI 装配 | ✓ | 配置、日志、异常、分页、中间件、依赖注入 |
| M0-4 身份与 RLS | ✓ | Alembic 首迁、`tenants/users/memberships`、登录/切换租户 |
| M0-5 Provider | ✓ | LLM / Embedding / Rerank 抽象 + Fake / OpenAI 兼容实现 |
| M0-6 CI | ✓ | ruff + mypy + pytest(≥70%) + eslint + tsc + gitleaks + 镜像构建 |
| M0-7 前端骨架 | ✓ | Vite + 登录页 + 布局 + HTTP/SSE + OpenAPI 类型基线 |

**本地验收命令**：

```bash
make bootstrap && make test && make lint
make api   # /healthz → 200；/docs 可登录
make web   # 用种子账号登录；两个租户交叉资源应返回 404
```

**种子账号**：`owner@acme.example` / `Passw0rd!2026`（同属两个租户，可验切换）。

### 下一步：M1 摄取链路（预计 2 周）

目标：上传一个 PDF，数据库里出现带页码坐标的 chunks。

| # | 任务 | 要点 |
| --- | --- | --- |
| M1-1 | 知识库 / 文档 CRUD + S3 预签名直传 | 沿用 03 文档上传协议 |
| M1-2 | Celery 双队列（parse / embed）+ 摄取状态机 | 解析调度单位是**页**（见 R1c） |
| M1-3 | PDF/DOCX 解析器 + OCR 回退 | 直接迁移 spike 的 normalize / heading / layout / ocr |
| M1-4 | 结构感知分块 + `clause_mode` | 流程工业模板开启条款式切分 |
| M1-5 | Embedding 写入 + HNSW | Fake Provider 可先通链路，再换真实模型 |
| M1-6 | 前端：拖拽上传、进度轮询、失败重试 | 文档详情页分块列表为 M3 铺路 |

**验收**：100 页真实手册 5 分钟内 `ready`；`chunk.content` 中标准号为半角 ASCII；抽查 `heading_path` / `page_start` 正确。

开工前用 `spikes/parse-quality` 对本批文档再跑一遍体检，fail 项写入本阶段验收用例。

---

## 2026-07-28

### 完成内容

#### 一、项目设计文档（提交 `a2145d8`）

从零建立六篇设计文档，确立了全部关键技术决策。

| 文档 | 核心产出 |
| --- | --- |
| 01 架构设计 | 模块化单体 + 解析 Worker 独立进程；Provider / Retriever 两层抽象；10 条 ADR |
| 02 数据模型 | 完整 DDL；共享库 + RLS + 应用层双重租户隔离；pgvector HNSW 与中文全文索引策略 |
| 03 API 设计 | REST/SSE 约定、端点清单、问答事件流、七图仪表盘只用三个接口 |
| 04 RAG 流水线 | 解析器矩阵、结构感知分块、混合检索 + RRF、引用校验、评测与排查手册 |
| 05 部署与运维 | 仓库结构、服务规格、可观测性、容量与成本测算 |
| 06 路线图 | M0–M5 里程碑、验收标准、风险登记表 |

期间按需求追加了**大模型接入管理**功能（01 文档 4.3）：接入点配置化、用途路由与故障转移、用量小时级预聚合、七张图表的可视化仪表盘。

#### 二、解析质量体检 spike（提交 `cd7e0b6`）

在写任何摄取代码之前验证 R1 解析风险，六项探针、坐标可视化、JSON 报告、退出码可接 CI。

#### 三、依据真实文档回改设计（提交 `e62c5f2`、`0d3e29b`）

用 6 份真实 AQ 安全标准（化工 3 份、烟花爆竹 3 份）跑体检，**发现 6 个原设计的错误假设并全部修正**。

### 实测数据

| 指标 | 结果 |
| --- | --- |
| 纯扫描件占比 | 3/6（化工类全部无文本层） |
| 文本层坐标质量 | 1108 span，零非法零越界 |
| OCR 坐标质量 | 168 span，零非法零越界，可视化确认框线贴合 |
| 字体错误映射 | 有文本层的 3 份全部中招，单份 117–346 处 |
| 全角字符占比 | 25%（文本层）/ 3.6%（OCR 输出） |
| OCR 单页耗时 | 中位 6.3 s，最大 10.6 s（200 dpi，PP-OCRv4） |
| OCR 置信度 | 均值 0.81，35.7% 低于 0.8 |

### 设计变更清单

| # | 发现 | 原设计 | 已改为 | 影响文档 |
| --- | --- | --- | --- | --- |
| 1 | 半数文档是纯扫描件 | OCR 放在 M3 | OCR 提到 M1 必做 | 06 |
| 2 | 拉丁字母被映射到汉字区，`AQ/T 4127` 变 `犃犙／犜４１２７` | 无此步骤 | 新增字符规范化，索引侧与查询侧共用一份 `normalize()` | 04 §2.3、§5.2 |
| 3 | 页眉底边 10.4%、正文顶边 11.0%，可用窗口仅 0.6% | 固定 8% 带宽 | 按 y 聚类取每页首尾行，不依赖比例常数 | 04 §2.3 |
| 4 | 国标写作「1范围」，编号后无分隔符 | `^\d+(\.\d+)*\s` | 允许编号后直接跟中文，识别数 0 → 21 | 04 §2.3 |
| 5 | 标准类文档结构单位是行首条款号而非标题行 | 仅按标题层级切分 | 新增 `clause_mode` 条款式切分 | 04 §3.2、§3.4 |
| 6 | OCR 单页 6.3 s，100 页串行需 10 分钟 | 解析按文档调度 | 解析改为**页级并行**调度 | 01 §5.1、§7.1 |

风险表新增 R1a–R1d 四条，状态均为"已发生"而非"可能发生"。

### 已验证成立的假设

- **ADR-005（坐标级引用溯源）成立**，且对文本层与 OCR 两种来源都成立。这是整套设计里牵连最广的一条，贯穿解析、`chunks.bboxes`、引用接口、前端 pdf.js 四层，它不塌意味着架构主干可以照原样往下走。
- 表格检测正常，最大 30 行的表可被识别，跨页表格嫌疑能自动标出。
- 页面尺寸全库一致，前端高亮层无需处理多尺寸换算的边缘情况。

---

## 进行中事项与待确认

> M0 任务表与验收命令见上文「2026-07-29」一节；此处只保留仍有效的迁移清单与开放问题。

### spike 成果的迁移

M1 开工时以下代码可直接从 `spikes/parse-quality/` 搬进主工程，不要重写：

| spike 中的位置 | 迁往 | 说明 |
| --- | --- | --- |
| `probes/encoding.py` 的 `CJK_LATIN_MAP` 与 `repair()` | `app/modules/ingestion/parsers/normalize.py` | 索引侧与查询侧必须共用这一份 |
| `probes/heading.py` 的 `NUMBERING` / `CLAUSE_INLINE` | `app/modules/ingestion/chunkers/` | 已按真实文档校准过的正则 |
| `probes/header_footer.py` 的行聚类算法 | `app/modules/ingestion/parsers/layout.py` | 替代原设计的固定带宽方案 |
| `ocr.py` 的坐标换算（像素 → pt） | `app/modules/ingestion/parsers/ocr.py` | `scale = 72 / dpi`，容易写错的一处 |
| `check.py` 整体 | `backend/scripts/parse_check.py` | 退出码已就绪，可直接接进 CI 做解析回归 |

### 待确认事项

不阻塞 M0；**需在 M1 之前有答复**。

| 事项 | 影响 | 建议何时确认 |
| --- | --- | --- |
| 首批目标行业具体是哪两个 | 内置 profile 模板优先级、评测集构建、`clause_mode` 默认值 | 立即 |
| 是否有文档密级要求 | 需在 `chunks` 加 `security_level` 并入检索过滤，现在加字段远比上线后便宜 | 立即 |
| 是否需要对接企业 SSO | `identity` 模块的认证扩展点 | M4 前 |
| 知识库之间是否需要资料复用 | 文档与知识库是否从一对多改为多对多 | M4 前 |
| 回答是否会被写入正式文件 | 引用快照与不可篡改审计的严格程度 | M4 前 |

### 仍存在的未知

| 未知 | 计划何时消除 |
| --- | --- |
| OCR 输出在**表格**上的还原质量（本次样本的表格都在文本层文档里） | M1，补一份带表格的扫描件进体检集 |
| 中文 Embedding 模型在工业术语上的实际召回率 | M2，用评测集标定 |
| 低置信度 OCR 文本对检索质量的实际影响幅度 | M2，对比开关该阈值的评测结果 |

---

## 变更记录

| 日期 | 提交 | 内容 |
| --- | --- | --- |
| 2026-07-29 | `f5b399b` | M0 工程骨架：后端身份/平台层、前端骨架、Compose、CI、Docker |
| 2026-07-28 | `bf9753d` | 进展与计划文档 |
| 2026-07-28 | `0d3e29b` | OCR 分支 + 页级并行 + 条款式分块 |
| 2026-07-28 | `e62c5f2` | 字符规范化 + 页眉页脚算法修正 |
| 2026-07-28 | `cd7e0b6` | 解析质量体检 spike |
| 2026-07-28 | `a2145d8` | 六篇设计文档 |
