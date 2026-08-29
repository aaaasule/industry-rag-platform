# 07 进展与计划

记录已完成的工作、由实测得出的结论，以及下一步的具体任务。每次推进后在此追加，不覆盖历史。

## 当前状态


| 项     | 值                                                                                        |
| ----- | ---------------------------------------------------------------------------------------- |
| 阶段    | **M0–M6 + P1 完成**（M6：知识库运营与检索智能化；验收修复 `my_permission` / settings 浅合并） |
| 下一里程碑 | **待产品拍板**：行业 golden 换真实 UUID 本地回归；或 Rerank 体验；或部署/SSO 方向 |
| 已落地   | 既有 M0–M5/P1/壳层/工作台；M6 W1–W4（PR [#35](https://github.com/aaaasule/industry-rag-platform/pull/35)）+ 验收修复（PR [#36](https://github.com/aaaasule/industry-rag-platform/pull/36)） |
| 阻塞项   | 行业 golden 的 `kb_id` / `expected_document_ids` 仍为 PLACEHOLDER，需本地 seed 真实语料后替换（**不**绑入 CI） |

---

## 2026-08-29（日进度 · M6 合入与验收修复）

### 结论

M6 全量已合入 `main`（PR [#35](https://github.com/aaaasule/industry-rag-platform/pull/35)，`f893b34`）。同日合入验收修复包（PR [#36](https://github.com/aaaasule/industry-rag-platform/pull/36)，`7b90ed8`）：写权限与后端对齐、settings 不再误整包冻结。

### 当日完成

| # | 事项 | 说明 |
| --- | --- | --- |
| 1 | M6 W1–W4 | 见下节交付一览；设计书 [`2026-08-28-m6-knowledge-ops-retrieval-design.md`](./superpowers/specs/2026-08-28-m6-knowledge-ops-retrieval-design.md) |
| 2 | 验收修复 | `KnowledgeBaseOut.my_permission`；前端 `canWrite` 按 `write\|manage`；PATCH settings 域内浅合并 + 脏键提交；设计/计划 [`2026-08-29-m6-permission-settings-fix-design.md`](./superpowers/specs/2026-08-29-m6-permission-settings-fix-design.md) |

### 下一步（待产品拍板）

1. 行业 golden 换真实 UUID 后本地 `evaluate.py`（仍不绑 CI）
2. Rerank 默认开 / Playground 与对比报告体验
3. 首发行业与语料、部署形态、是否 SSO

---

## 2026-08-29（日进度 · M6 W1–W4 交付备注）

### 结论

M6（设计书 [`2026-08-28-m6-knowledge-ops-retrieval-design.md`](./superpowers/specs/2026-08-28-m6-knowledge-ops-retrieval-design.md)）四周能力已合入 `main`（PR [#35](https://github.com/aaaasule/industry-rag-platform/pull/35)）：运营面（enabled/batch/审计）、KB 调参、查询理解、行业种子与评测占位。CI 仍只跑 `golden.ci.jsonl`，阈值不变。

### W1–W4 交付一览

| 周 | 主题 | 交付 |
| --- | --- | --- |
| W1 | 文档运营 | `documents.enabled` + 检索过滤；PATCH 单文档；`POST .../documents/batch`（≤50）；upload/delete/ingest 审计；文件表开关与批量 UI |
| W2 | KB 调参 | KB `settings` PATCH（chunk/retrieval 覆盖 Profile）；配置页可编辑；检索测试读 effective 规则 |
| W3 | 查询理解 | Chat 多轮指代改写（`rewrite`）；Profile/KB `retrieval_rules.query_expand` + Playground 单次覆盖；融合分过低时二次扩展 |
| W4 | 行业打磨 | `discrete_manufacturing.overlap_tokens`→**128**；`process_industry` dictionary 增加 **`GB/T`、`AQ/T`**；元数据抽屉；`evals/golden.discrete.jsonl` / `golden.process.jsonl`（≥10 条，PLACEHOLDER UUID） |

### 行业 golden 占位说明（替换真实 ID）

1. `make seed` 后创建/选用对应行业模板的知识库，上传手册/规程至 `ready`。
2. 在 `backend/evals/golden.discrete.jsonl`、`golden.process.jsonl` 中，将 `019d15c0-…` / `019f1000-…` 等 **PLACEHOLDER** 换为真实 `kb_id` 与 `expected_document_ids`（文件顶部 `#` 注释有示例命令）。
3. 本地评测（**勿**改 CI / `golden.ci.jsonl`）：

```bash
cd backend && uv run python scripts/evaluate.py \
  --base http://127.0.0.1:8000/api/v1 \
  --email <email> --password '<pw>' --tenant <slug> \
  --kb-id <真实-kb-uuid> --golden evals/golden.discrete.jsonl --k 10
# process 同理换 --golden evals/golden.process.jsonl
```

4. 刷新内置模板规则：本地再跑一次 `make seed`（seed 会对 builtin profile refresh）。

### 明确不做（本里程碑）

RRF 权重调参、自动全库 reingest、图谱、SSO、HTML 解析、CI 绑定行业 golden 硬失败。

---

## 2026-08-28（日进度 · 壳层改版与 P1/P2 收口）

### 结论

PR [#29](https://github.com/aaaasule/industry-rag-platform/pull/29)（个人资料、浅色壳层、会话搜索）、PR [#30](https://github.com/aaaasule/industry-rag-platform/pull/30)（Lucide 统一、概览/登录/知识库对齐）、PR [#31](https://github.com/aaaasule/industry-rag-platform/pull/31)（P2 运营/用量视觉与工程质量）、PR [#32](https://github.com/aaaasule/industry-rag-platform/pull/32)（知识库四 Tab 工作台）、PR [#33](https://github.com/aaaasule/industry-rag-platform/pull/33)（文档连续滑动预览）已合入 `main`。

### 当日完成

| # | 事项 | 说明 |
| --- | --- | --- |
| 1 | 个人资料 + 壳层 | PR #29：DeepSeek 风格侧栏（折叠记忆、底部用户区）；`PATCH /auth/me`、`POST /auth/change-password`；会话列表搜索 + 时间分组 |
| 2 | P1 视觉统一 | PR #30：全站 Lucide；概览/登录/知识库对齐浅色壳层；「更早」分组；侧栏帮助文档外链 |
| 3 | P2 运营/用量 | Admin / UsageDashboard / 共享 Tabs·Chip·PageHeader 对齐 Indigo+Slate；图表色板更新 |
| 4 | P2 工程质量 | `auth/api.ts` 改从 `openapi.gen.ts` 派生类型；OpenAPI 同步 PATCH/change-password；`Makefile` 新增 `make beat` |
| 5 | 用量数据链路 | 本地需同时跑 `make worker` + `make beat`，Redis 缓冲 → flush（60s）→ hourlies（3600s）后仪表盘才有数据 |
| 6 | 知识库工作台 | PR #32：路由 `/knowledge/:kbId/{files|retrieval|logs|settings}`；侧栏四 Tab；检索测试 POST `/search`；审计日志过滤；配置页名称/描述/模板/授权；设计书 [`2026-08-28-knowledge-module-redesign-design.md`](./superpowers/specs/2026-08-28-knowledge-module-redesign-design.md) |
| 7 | 文档滑动预览 | PR #33：`PdfHighlightViewer` 全页纵向连续滚动 + IntersectionObserver 同步页码；点击分块 `scrollIntoView` 高亮；文本预览滚动布局对齐 |

### 本地联调（用量仪表盘）

```bash
make up && make migrate && make seed
make api          # 终端 1
make worker       # 终端 2（ingest / embed / stats 队列）
make beat         # 终端 3（用量 flush + hourlies 预聚合）
make web          # 终端 4
# 登录 owner/admin → 用量：产生 chat/search 调用后约 1 分钟内可见
```

### 下一步（待产品拍板）

1. 首发行业与语料、部署形态（内网/云）、是否 SSO / 跨租户复用
2. 有痛点再开工程：页级 Celery chord、查询改写/指代消解、golden 固化、暗色主题等
3. 路线图 M6 演进项（重排默认开、图谱、Agent…）仅在触发条件成立时启动

---

## 2026-08-27（日进度 · 合入与收口）

### 结论

工程面 **收口**：modelops 平台探测 RLS 缺陷已修；前端 Cobalt+Slate 视觉 P1/P2 合入 `main`。下一里程碑 **M6 仍待定**，需产品先定首发行业、部署形态与 SSO 等方向。

### 当日完成

| # | 事项 | 说明 |
| --- | --- | --- |
| 1 | modelops RLS | PR [#27](https://github.com/aaaasule/industry-rag-platform/pull/27)：`test()` 对 `tenant_id = NULL` 的平台行跳过 `health` 写入，仅返回探测结果 → `f5507f5` |
| 2 | 前端视觉 P1 | PR [#26](https://github.com/aaaasule/industry-rag-platform/pull/26) Part 1：Design tokens（Cobalt+Slate）、Plus Jakarta / Noto Sans SC / IBM Plex Mono、Phosphor 图标；`components/ui` 共享组件；Sidebar + 精简顶栏；Login / Overview / Knowledge / KbDetail / Chat（拆分为 Toolbar / MessageList / Composer / ConversationList） |
| 3 | 前端视觉 P2 | 同上 PR Part 2：Admin、UsageDashboard、DocumentDetail、EvidencePanel / ChatRightPanel 对齐新视觉 |
| 4 | 规格文档 | [`2026-08-27-frontend-refresh-p1-design.md`](./superpowers/specs/2026-08-27-frontend-refresh-p1-design.md)、[`p2-design.md`](./superpowers/specs/2026-08-27-frontend-refresh-p2-design.md)；旧 `2026-08-05-frontend-visual-system-design.md` 标记 superseded |
| 5 | 验证 | `pnpm lint && pnpm typecheck && pnpm build` 通过；核心旅程冒烟：登录 → 概览 → 建库 → 问答 → 证据 |

### 实测要点

| 项 | 内容 |
| --- | --- |
| 日期 | 2026-08-27 |
| modelops | 平台接入点「测试连接」不再触发 `InsufficientPrivilegeError`；租户行仍正常持久化 health |
| 前端 | 冷色 B2B 专业系；`< lg` 侧栏 drawer；路由未变；暗色主题仍为后置项 |

### 下一步（待产品拍板）

1. 首发行业与语料、部署形态（内网/云）、是否 SSO / 跨租户复用  
2. 有痛点再开工程：页级 Celery chord、查询改写/指代消解、golden 固化、暗色主题等  
3. 路线图 M6 演进项（重排默认开、图谱、Agent…）仅在触发条件成立时启动  

---

## 2026-08-26（日进度 · E2E 验收收口）

### 结论

真实行业语料 E2E **通过**；摄取 NUL 缺陷已修并合入 `main`。下一里程碑 **M6 待定**（先定产品/部署，再选工程刀）。

### 当日完成

| # | 事项 | 说明 |
| --- | --- | --- |
| 1 | 本地依赖 | Worker 连不上 Redis（`6380`）：基础设施未起 → `make up` / compose 拉起 redis·postgres·minio |
| 2 | E2E 验收 | 清单 A–F 勾完（环境、摄取、检索/对话、Profile 边角、golden）；结论 **通过** |
| 3 | 摄取修复 | 大 PDF 解析写 `document_pages` 失败：`\u0000` → Postgres 拒收；`normalize` + 入库前 scrub |
| 4 | 合入 | PR [#25](https://github.com/aaaasule/industry-rag-platform/pull/25) squash → `main`（`fc33e35`） |
| 5 | 文档 | README / 07 进展：阶段改为「M0–M5 + P1 完成，E2E 通过」 |

### 实测要点

| 项 | 内容 |
| --- | --- |
| 日期 | 2026-08-26 |
| 范围 | 真实语料摄取 → ready；Search/Chat；Profile；golden 评测 |
| 阻断问题 | PDF 抽取含 NUL（已修） |
| 明确不做（当日） | 不自动开 M6；chord / LLM 查询改写仍为可选后置 |

### 下一步（待产品拍板）

1. 首发行业与语料、部署形态（内网/云）、是否 SSO / 跨租户复用  
2. 有痛点再开工程：页级 Celery chord、查询改写/指代消解、富预览等  
3. 路线图 M6 演进项（重排默认开、图谱、Agent…）仅在触发条件成立时启动  

---

## 2026-08-18（P1 批次 D · Profile 运营 + 术语归一）

### 进行中 / 本批目标


| #   | 任务                                | 状态  |
| --- | --------------------------------- | --- |
| D-1 | 查询侧 `parse_rules.synonyms` 最长匹配替换 | ✓   |
| D-2 | Profile 软删恢复 + `include_deleted`  | ✓   |
| D-3 | 术语表 / 同义词 / metadata_schema 表单    | ✓   |
| D-4 | 测试 / 设计短文                         | ✓   |


**决策**：同义词只改查询、不重摄取；不做 LLM 改写 / 指代消解。  
**合并**：PR [#24](https://github.com/aaaasule/industry-rag-platform/pull/24) squash → `main`。

---



## 2026-08-14（P1 批次 C · 重新生成 + 非 PDF 预览）



### 进行中 / 本批目标


| #   | 任务                                            | 状态  |
| --- | --------------------------------------------- | --- |
| C-1 | `POST /messages/{id}/regenerate` 原地重跑 SSE     | ✓   |
| C-2 | 问答页最后一条助手消息「重新生成」                             | ✓   |
| C-3 | `GET /documents/{id}/pages` + 非 PDF 正文预览与分块联动 | ✓   |
| C-4 | 测试 / 设计短文                                     | ✓   |


**决策**：只重跑会话最后一条助手消息；非 PDF 用解析页文本高亮，不做 bbox。  
**合并**：PR [#23](https://github.com/aaaasule/industry-rag-platform/pull/23) squash → `main`。

---



## 2026-08-14（P1 批次 B · KB 授权 UI + 无邮件邀请）



### 进行中


| #   | 任务                                 | 状态  |
| --- | ---------------------------------- | --- |
| B-1 | 成员邀请：不存在则建号 + `temporary_password` | ✓   |
| B-2 | Admin 成员面板展示初始口令                   | ✓   |
| B-3 | KB grants UI（详情页）+ GrantOut 带邮箱    | ✓   |
| B-4 | 测试 / 设计短文                          | ✓   |


**决策**：无 SMTP；`create_if_missing` 默认 true；授权仅限本租户成员。  
**合并**：PR [#22](https://github.com/aaaasule/industry-rag-platform/pull/22) squash → `main`。

---



## 2026-08-14（P1 批次 A · 解析与摄取）



### 进行中 / 本批目标


| #   | 任务                                       | 状态  |
| --- | ---------------------------------------- | --- |
| A-1 | DOCX / XLSX / PPTX / MD·TXT 解析 + mime 分派 | ✓   |
| A-2 | PDF OCR 文档内线程池并行 + Redis 进度              | ✓   |
| A-3 | `GET /documents/{id}/events` SSE         | ✓   |
| A-4 | 详情页 SSE；列表轮询；上传 accept 扩展                | ✓   |
| A-5 | 单测夹具；Celery chord **后置**；`.md` mime 纠正   | ✓   |


**决策**：非 PDF 仅可检索、预览仍「暂不支持」；chord 页级任务 follow-up。  
**合并**：PR [#21](https://github.com/aaaasule/industry-rag-platform/pull/21) squash → `main`。

---



## 下一步：真实行业语料 E2E 验收清单

CI 合成语料只能防回归；上线前需用**真实文档 + 真实问题**跑通一遍。建议按序勾选。

### A. 环境与账号

- [x] `docker compose up` / 本地 Postgres+Redis+API+Worker 可用
- [x] 租户账号可登录控制台；Provider（embedding / chat）连接探测通过
- [x] 选好目标行业 Profile（或新建自定义 Profile：chunk / hybrid / dictionary）



### B. 知识库与摄取

- [x] 新建 KB，绑定该 Profile
- [x] 上传 ≥3 份真实文档（PDF/DOCX/Markdown 等平台已支持格式）
- [x] 文档状态全部变为 `ready`（失败则记录错误码与日志）
- [x] 若 Profile 配了 `metadata_schema`：合法 metadata 可注册；未知字段 / 类型错误 → 422 `metadata_invalid`
- [x] 若配了 `parse_rules.dictionary`：专业词在分块/检索侧可按预期切出（抽 1–2 个词人工核对）



### C. 检索与对话

- [x] Search：用业务口吻提问，Top-K 命中相关 chunk；引用/来源可点开
- [x] Chat：答案有依据、不胡编；无检索结果时行为可接受
- [x] 空库 / 空结果：EmptyState 与 toast 提示清晰



### D. Profile 与权限边角

- [x] 自定义 Profile 可编辑；软删除后列表不可见；有 KB 引用时 409 `profile_in_use`
- [x] 内置模板不可删
- [x] 非管理员无法改连接 / 删 Profile（按现有 RBAC）



### E. 离线评测（真实 golden）

- [x] 整理 ≥10 条真实问答 → `evals/golden.<行业>.jsonl`（含 `expected_doc_ids` 或等价标签）
- [x] `make eval` / `scripts/evaluate.py` 对本地 API 跑通；记录 Recall@10、MRR
- [x] 指标不达标时：先调 Profile（词典、chunk、hybrid 权重），再考虑新能力（勿先上图谱/Agent）



### F. 验收结论（写入本节下方「实测记录」）

- [x] 通过 / 有条件通过 / 不通过
- [x] 主要问题列表（按严重度）
- [x] 是否启动 M6，以及 M6 仅包含哪些项



### 产品开放问题（验收前后可并行回答）

1. 首发目标行业与语料来源？
2. 部署安全级别（内网 / 专有云 / 公有云）？
3. 是否需要 SSO？
4. 知识库是否跨租户复用？



### 实测记录

见上文「2026-08-26（日进度 · E2E 验收收口）」：结论 **通过**；修复 PDF `\u0000` 入库失败。

---



## 2026-08-05（M5 · 缺口与工程债收尾）



### 完成内容


| #   | 任务                                                                                     | 状态  |
| --- | -------------------------------------------------------------------------------------- | --- |
| M-1 | `validate_document_metadata` + `register_document` 接入 EffectiveProfile.metadata_schema | ✓   |
| M-2 | Profile 软删（`deleted_at` 迁移、DELETE API、409 `profile_in_use`）+ 前端删除入口                    | ✓   |
| M-3 | `parse_rules.dictionary` → jieba userdict；摄取与检索 query 分词共用                             | ✓   |
| M-4 | discrete 种子模板补充 industry 词典                                                            | ✓   |
| E-1 | `evaluate.py` 支持 `--min-recall` / `--min-mrr`；无标签样本 exit 2                             | ✓   |
| E-2 | `seed_eval_ci.py` + `golden.ci.jsonl`（固定 UUID 幂等 seed）                                 | ✓   |
| E-3 | CI `eval` job + Makefile `eval-ci`（Recall@10=1.0、MRR=1.0 硬失败）                          | ✓   |


**决策**：Profile 软删不回物理删；内置模板不可删；CI 评测与 backend job 并行、自带 Postgres/Redis；OpenAPI 同步 industry-profiles CRUD。  
**合并**：PR [#19](https://github.com/aaaasule/industry-rag-platform/pull/19) squash → `main`。

---



## 2026-08-05（前端 · 工业控制台视觉 P1–P3）



### 完成内容


| #   | 任务                                                | 状态  |
| --- | ------------------------------------------------- | --- |
| V-1 | 规格 / 计划                                           | ✓   |
| V-2 | CSS tokens + Tailwind brand→铁青 + 字体               | ✓   |
| V-3 | AppLayout 顶栏 / Login 左右分栏                         | ✓   |
| V-4 | Overview 轻工作台快捷入口                                 | ✓   |
| V-5 | Knowledge 列表 / 详情 / 文档页样式对齐                       | ✓   |
| V-6 | Admin / Profiles / Connections / Usages / Chat 表面 | ✓   |
| V-7 | 行业模板表单 + JSON 双视图（Tab 双向合并）                       | ✓   |


**决策**：整站视觉升级、IA 不动；工业控制台气质；分 P1/P2/P3；双视图常用字段 + 未知键保留。

---



## 2026-08-04（chore · Backend CI）



### 完成内容


| #    | 任务                                            | 状态  |
| ---- | --------------------------------------------- | --- |
| CI-1 | ruff format 未过的 5 个文件                         | ✓   |
| CI-2 | CI 增加 Postgres(pgvector)+Redis、角色初始化与 migrate | ✓   |


**根因**：#14 Backend 在 Ruff format --check 失败（非 Postgres）；且 workflow 历来无 DB service，format 修好后 pytest 仍会挂。

---



## 2026-08-04（M5 · Profile CRUD + UI + evaluate）



### 完成内容


| #   | 任务                                           | 状态  |
| --- | -------------------------------------------- | --- |
| C-1 | POST/PATCH `/industry-profiles`（admin，内置只读）  | ✓   |
| C-2 | KB `profile_code` 改绑                         | ✓   |
| C-3 | Admin tab「行业模板」JSON 编辑                       | ✓   |
| C-4 | KbDetail 改绑 UI                               | ✓   |
| D-1 | `scripts/evaluate.py` + `evals/golden.jsonl` | ✓   |


**决策**：先 C 后 D；派生后编辑；evaluate 不阻断 CI。

---



## 2026-08-04（M5 · prompt + retrieval 接入）



### 完成内容


| #   | 任务                                             | 状态  |
| --- | ---------------------------------------------- | --- |
| B-1 | 规格 / 计划                                        | ✓   |
| B-2 | `build_messages(system_override)`              | ✓   |
| B-3 | chat 检索 top_k/rerank + system 走 resolve（首个 KB） | ✓   |
| B-4 | `/search` 缺省 top_k/rerank 走 resolve            | ✓   |
| B-5 | process_industry 种子 system；单测                  | ✓   |


**决策**：多 KB 取 `kb_ids[0]`；`rerank_enabled is None` 回退 env；`top_k=None` 表示未传。

---



## 2026-08-04（M5 · EffectiveProfile resolve）



### 完成内容


| #   | 任务                                        | 状态  |
| --- | ----------------------------------------- | --- |
| P-1 | 规格                                        | ✓   |
| P-2 | `EffectiveProfile` + `resolve(kb_id)` 浅合并 | ✓   |
| P-3 | 摄取分块改走 resolve                            | ✓   |
| P-4 | 单测（合并优先级 / clause_mode）                   | ✓   |
| P-5 | `GET /industry-profiles` 返回 `chunk_rules` | ✓   |


**决策**：本切片不含 CRUD/前端/prompt/eval；KB.settings 域浅覆盖 profile。

---



## 2026-08-04（M4 · QPS/并发限流）



### 完成内容


| #   | 任务                               | 状态  |
| --- | -------------------------------- | --- |
| R-1 | 规格 / 计划                          | ✓   |
| R-2 | `RateLimiter` + Settings         | ✓   |
| R-3 | chat QPS+并发（SSE 全程占坑）；search QPS | ✓   |
| R-4 | 集成 / 单元测试                        | ✓   |


**决策**：Redis 故障放行；limit≤0 关闭；并发占到 SSE 结束。

---



## 2026-08-04（M4 · 运营 UI）



### 完成内容


| #   | 任务                               | 状态  |
| --- | -------------------------------- | --- |
| O-1 | 规格 / 计划                          | ✓   |
| O-2 | `api.put` + worker F401 修复       | ✓   |
| O-3 | 接入点面板（CRUD / 凭证 / test / routes） | ✓   |
| O-4 | 成员 + 审计面板                        | ✓   |
| O-5 | `/admin` 导航与 `/modelops` 重定向     | ✓   |


**决策**：单入口 Tab；平台接入点只读；不含 KB grants UI。

---



## 2026-08-04（M4 · 用量仪表盘）



### 完成内容


| #   | 任务                                                        | 状态  |
| --- | --------------------------------------------------------- | --- |
| D-1 | 规格 / 计划                                                   | ✓   |
| D-2 | series `latency_p95_ms`；breakdown `user`/`knowledge_base` | ✓   |
| D-3 | OpenAPI 同步 + `features/usages`                            | ✓   |
| D-4 | 七图仪表盘 + admin 导航                                          | ✓   |


**决策**：客户演示级；user/kb 走明细聚合；熔断标注不做；运营 UI 下一刀。

---



## 2026-08-04（M4 · 配额 429）



### 完成内容


| #   | 任务                                     | 状态  |
| --- | -------------------------------------- | --- |
| Q-1 | 规格 / 计划                                | ✓   |
| Q-2 | `QuotaExceeded` + `Retry-After`        | ✓   |
| Q-3 | `QuotaService`（hourlies + Redis 5min）  | ✓   |
| Q-4 | chat / search 挂载 `require_token_quota` | ✓   |
| Q-5 | 集成测试                                   | ✓   |


**决策**：仅 `monthly_tokens`；`limit≤0` 不限额；错误码 `quota_exceeded`。

---



## 2026-07-30（M4 · health 故障转移）



### 完成内容


| #   | 任务                                        | 状态  |
| --- | ----------------------------------------- | --- |
| H-1 | 规格 / 计划                                   | ✓   |
| H-2 | `probe_connection` 共用探针                   | ✓   |
| H-3 | `/test` 失败写 `down`                        | ✓   |
| H-4 | `ProviderFactory` 跳过 `down`，全 down → env  | ✓   |
| H-5 | Celery `modelops.probe_connections`（300s） | ✓   |
| H-6 | 集成测试                                      | ✓   |


**决策**：仅定时探测改 health；路由只跳过 `down`；不写 `degraded`；无前端。

---



## 2026-07-30（M4 · 用量埋点）



### 完成内容


| #   | 任务                                              | 状态     |
| --- | ----------------------------------------------- | ------ |
| U-1 | 规格                                              | ✓      |
| U-2 | 迁移 `0007`：pricing / usages / hourlies + RLS     | ✓      |
| U-3 | `UsageRecorder` → Redis；Celery flush + hourlies | ✓      |
| U-4 | chat / retrieval / ingestion 埋点                 | ✓      |
| U-5 | `GET /usages/summary                            | series |
| U-6 | seed 占位定价 + 测试                                  | ✓      |


**决策**：方案 1 扩展 modelops；Redis 缓冲；成本写入快照；本切片无前端、无配额 429、usages 不分区。

---



## 2026-07-30（M4 · 模型接入点）



### 完成内容


| #   | 任务                                        | 状态  |
| --- | ----------------------------------------- | --- |
| C-1 | 规格 / 计划                                   | ✓   |
| C-2 | 迁移 `0006` + Fernet 凭证                     | ✓   |
| C-3 | `/model-connections` CRUD / test / routes | ✓   |
| C-4 | `ProviderFactory` 租户→平台→env               | ✓   |
| C-5 | chat / retrieval / ingestion 接线           | ✓   |
| C-6 | seed 平台接入点                                | ✓   |


**决策**：凭证应用层加密；本切片不做 health 故障转移与用量。

---



## 2026-07-29（M4 · 成员管理 + 审计）



### 完成内容


| #   | 任务                                              | 状态  |
| --- | ----------------------------------------------- | --- |
| A-1 | 规格 / 计划                                         | ✓   |
| A-2 | 迁移 `0005_audit_logs` + RLS                      | ✓   |
| A-3 | `AuditService.record` + `GET /admin/audit-logs` | ✓   |
| A-4 | `/memberships` CRUD（admin+，邮箱加人）                | ✓   |
| A-5 | 钩子：成员 / grant / 删 KB / login / switch-tenant    | ✓   |
| A-6 | 集成测试                                            | ✓   |


**决策**：加人仅限已存在用户；审计写入失败不阻断主业务；admin 不可改/删 owner。

---



## 2026-07-29（M4 · kb_grants）



### 完成内容


| #   | 任务                                                    | 状态  |
| --- | ----------------------------------------------------- | --- |
| G-1 | `KbGrant` ORM + `identity.permissions.visible_kb_ids` | ✓   |
| G-2 | KB list/get/写操作按权限收窄；同租户无权 403                        | ✓   |
| G-3 | grants CRUD API                                       | ✓   |
| G-4 | search/chat 走同一可见集                                    | ✓   |
| G-5 | 跨租户 / private / 授撤权 / owner 绕过测试                      | ✓   |


**决策**：owner/admin 对本租户全部 KB 视为 manage；`manage` ⊃ `write` ⊃ `read`。

---



## 2026-07-29（M3 引用溯源）



### 完成内容（进行中 → 代码已落地）


| #    | 任务                                                            | 状态  |
| ---- | ------------------------------------------------------------- | --- |
| M3-1 | 规格 / 计划                                                       | ✓   |
| M3-2 | `GET /documents/{id}/chunks`                                  | ✓   |
| M3-3 | 迁移 `0004` + `POST /messages/{id}/feedback`                    | ✓   |
| M3-4 | `MessageOut`：`document_title` / `used_citations` / `feedback` | ✓   |
| M3-5 | 共享 `PdfHighlightViewer`（react-pdf）                            | ✓   |
| M3-6 | 问答右栏列表⇄PDF + 赞踩 + used 置灰                                     | ✓   |
| M3-7 | 文档详情双栏 + 列表入口                                                 | ✓   |


**范围**：标准 M3 核心（方案 A）；不做重新生成 / XLSX·PPTX·MD 解析。

**本地**：`make migrate` 后起 api/web；点 `[n]` 看右栏高亮；知识库文档标题进详情。

---



## 2026-07-29（真实 Embedding / LLM / Rerank）



### 完成内容


| #   | 任务                                                          | 状态     |
| --- | ----------------------------------------------------------- | ------ |
| P-1 | Settings：LLM / Embedding / Rerank 独立 base_url、api_key       | ✓      |
| P-2 | Embedding：`dimensions=1024`，`batch_size≤10`（DashScope）      | ✓      |
| P-3 | Rerank：`compatible-api` + `/reranks` + `qwen3-rerank`；检索默认开 | ✓      |
| P-4 | AQ4102 文档 reingest（真实向量）→ `ready`                           | ✓ ~10s |
| P-5 | `scripts/compare_retrieval.py`：RRF vs RRF+rerank 报告         | ✓      |
| P-6 | DeepSeek `deepseek-v4-flash` SSE 问答 → `done`                | ✓      |


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


| #        | 任务                                                                                     | 状态  |
| -------- | -------------------------------------------------------------------------------------- | --- |
| M2-1     | 迁移 `0003`：conversations / messages / citations + RLS + ORM                             | ✓   |
| M2-2     | `rrf_fuse` + `validate_citations` 纯函数与单测                                               | ✓   |
| M2-3     | RetrievalService：normalize + 向量/全文 + RRF + expand；`POST /search`                       | ✓   |
| M2-4     | Chat SSE：`message_created`→`retrieval`→`citations`/`delta`/`done` 或 `no_answer`；会话 API | ✓   |
| M2-5     | 前端 `/chat`：多 KB 选择、流式渲染、证据面板                                                           | ✓   |
| M2-验收·检索 | AQ4102 KB：`/search` 命中 5 条，含 `scores.rrf` / `vector` / `fulltext`                      | ✓   |
| M2-验收·问答 | 同 KB SSE：`message_created`…`citations`…`delta*`…`done`                                 | ✓   |


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


| #         | 任务                                      | 状态                                                     |
| --------- | --------------------------------------- | ------------------------------------------------------ |
| M1-1      | 知识库 / 文档 CRUD + 预签名 + multipart 上传      | ✓                                                      |
| M1-2      | Celery 双队列 parse / embed + 状态机          | ✓                                                      |
| M1-3      | PDF 文本层解析 + OCR 回退 + normalize / layout | ✓（`uv sync --extra ocr`；Intel Mac 钉住 onnxruntime<1.24） |
| M1-4      | 结构感知分块 + `clause_mode`                  | ✓                                                      |
| M1-5      | Embedding 写入 + HNSW（Fake Provider）      | ✓                                                      |
| M1-6      | 前端：知识库列表、拖拽上传、进度轮询、失败重试                 | ✓                                                      |
| M1-验收·文本层 | AQ4102（17 页）→ `ready`，约 8s，12 chunks    | ✓                                                      |
| M1-验收·扫描件 | OCR 依赖修复后对失败文档重试                        | ✓ AQ3072（8 页扫描）parse≈108s → `ready`                    |


**已知遗留（不阻塞 M2）**：DOCX 解析、SSE 进度（现为轮询）、页级 Celery 并行（R1c）、100 页手册性能压测。

**下一步**：开 `feat/m2-retrieval`——向量 + 全文 + RRF、`POST /search`、流式问答 SSE。

---



## 2026-07-29（续）



### 进行中：M1 摄取链路


| #     | 任务                                      | 状态                                      |
| ----- | --------------------------------------- | --------------------------------------- |
| M1-1  | 知识库 / 文档 CRUD + 预签名 + multipart 上传      | ✓                                       |
| M1-2  | Celery 双队列 parse / embed + 状态机          | ✓                                       |
| M1-3  | PDF 文本层解析 + OCR 回退 + normalize / layout | ✓（OCR 为可选 extra）                        |
| M1-4  | 结构感知分块 + `clause_mode`                  | ✓                                       |
| M1-5  | Embedding 写入 + HNSW（Fake Provider）      | ✓                                       |
| M1-6  | 前端：知识库列表、拖拽上传、进度轮询、失败重试                 | ✓                                       |
| M1-验收 | 真实手册端到端 `ready`                         | ✓ AQ4102（17 页文本层）约 8s → ready，12 chunks |


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


| 任务              | 状态  | 产出                                                          |
| --------------- | --- | ----------------------------------------------------------- |
| M0-1 monorepo   | ✓   | `backend/` + `frontend/` + `deploy/` + `Makefile`           |
| M0-2 Compose    | ✓   | Postgres 16 + pgvector / Redis / MinIO                      |
| M0-3 FastAPI 装配 | ✓   | 配置、日志、异常、分页、中间件、依赖注入                                        |
| M0-4 身份与 RLS    | ✓   | Alembic 首迁、`tenants/users/memberships`、登录/切换租户              |
| M0-5 Provider   | ✓   | LLM / Embedding / Rerank 抽象 + Fake / OpenAI 兼容实现            |
| M0-6 CI         | ✓   | ruff + mypy + pytest(≥70%) + eslint + tsc + gitleaks + 镜像构建 |
| M0-7 前端骨架       | ✓   | Vite + 登录页 + 布局 + HTTP/SSE + OpenAPI 类型基线                   |


**本地验收命令**：

```bash
make bootstrap && make test && make lint
make api   # /healthz → 200；/docs 可登录
make web   # 用种子账号登录；两个租户交叉资源应返回 404
```

**种子账号**：`owner@acme.example` / `Passw0rd!2026`（同属两个租户，可验切换）。

### 下一步：M1 摄取链路（预计 2 周）

目标：上传一个 PDF，数据库里出现带页码坐标的 chunks。


| #    | 任务                               | 要点                                              |
| ---- | -------------------------------- | ----------------------------------------------- |
| M1-1 | 知识库 / 文档 CRUD + S3 预签名直传         | 沿用 03 文档上传协议                                    |
| M1-2 | Celery 双队列（parse / embed）+ 摄取状态机 | 解析调度单位是**页**（见 R1c）                             |
| M1-3 | PDF/DOCX 解析器 + OCR 回退            | 直接迁移 spike 的 normalize / heading / layout / ocr |
| M1-4 | 结构感知分块 + `clause_mode`           | 流程工业模板开启条款式切分                                   |
| M1-5 | Embedding 写入 + HNSW              | Fake Provider 可先通链路，再换真实模型                      |
| M1-6 | 前端：拖拽上传、进度轮询、失败重试                | 文档详情页分块列表为 M3 铺路                                |


**验收**：100 页真实手册 5 分钟内 `ready`；`chunk.content` 中标准号为半角 ASCII；抽查 `heading_path` / `page_start` 正确。

开工前用 `spikes/parse-quality` 对本批文档再跑一遍体检，fail 项写入本阶段验收用例。

---



## 2026-07-28



### 完成内容



#### 一、项目设计文档（提交 `a2145d8`）

从零建立六篇设计文档，确立了全部关键技术决策。


| 文档         | 核心产出                                                      |
| ---------- | --------------------------------------------------------- |
| 01 架构设计    | 模块化单体 + 解析 Worker 独立进程；Provider / Retriever 两层抽象；10 条 ADR |
| 02 数据模型    | 完整 DDL；共享库 + RLS + 应用层双重租户隔离；pgvector HNSW 与中文全文索引策略      |
| 03 API 设计  | REST/SSE 约定、端点清单、问答事件流、七图仪表盘只用三个接口                        |
| 04 RAG 流水线 | 解析器矩阵、结构感知分块、混合检索 + RRF、引用校验、评测与排查手册                      |
| 05 部署与运维   | 仓库结构、服务规格、可观测性、容量与成本测算                                    |
| 06 路线图     | M0–M5 里程碑、验收标准、风险登记表                                      |


期间按需求追加了**大模型接入管理**功能（01 文档 4.3）：接入点配置化、用途路由与故障转移、用量小时级预聚合、七张图表的可视化仪表盘。

#### 二、解析质量体检 spike（提交 `cd7e0b6`）

在写任何摄取代码之前验证 R1 解析风险，六项探针、坐标可视化、JSON 报告、退出码可接 CI。

#### 三、依据真实文档回改设计（提交 `e62c5f2`、`0d3e29b`）

用 6 份真实 AQ 安全标准（化工 3 份、烟花爆竹 3 份）跑体检，**发现 6 个原设计的错误假设并全部修正**。

### 实测数据


| 指标       | 结果                                   |
| -------- | ------------------------------------ |
| 纯扫描件占比   | 3/6（化工类全部无文本层）                       |
| 文本层坐标质量  | 1108 span，零非法零越界                     |
| OCR 坐标质量 | 168 span，零非法零越界，可视化确认框线贴合            |
| 字体错误映射   | 有文本层的 3 份全部中招，单份 117–346 处           |
| 全角字符占比   | 25%（文本层）/ 3.6%（OCR 输出）               |
| OCR 单页耗时 | 中位 6.3 s，最大 10.6 s（200 dpi，PP-OCRv4） |
| OCR 置信度  | 均值 0.81，35.7% 低于 0.8                 |




### 设计变更清单


| #   | 发现                                   | 原设计              | 已改为                               | 影响文档         |
| --- | ------------------------------------ | ---------------- | --------------------------------- | ------------ |
| 1   | 半数文档是纯扫描件                            | OCR 放在 M3        | OCR 提到 M1 必做                      | 06           |
| 2   | 拉丁字母被映射到汉字区，`AQ/T 4127` 变 `犃犙／犜４１２７` | 无此步骤             | 新增字符规范化，索引侧与查询侧共用一份 `normalize()` | 04 §2.3、§5.2 |
| 3   | 页眉底边 10.4%、正文顶边 11.0%，可用窗口仅 0.6%     | 固定 8% 带宽         | 按 y 聚类取每页首尾行，不依赖比例常数              | 04 §2.3      |
| 4   | 国标写作「1范围」，编号后无分隔符                    | `^\d+(\.\d+)*\s` | 允许编号后直接跟中文，识别数 0 → 21             | 04 §2.3      |
| 5   | 标准类文档结构单位是行首条款号而非标题行                 | 仅按标题层级切分         | 新增 `clause_mode` 条款式切分            | 04 §3.2、§3.4 |
| 6   | OCR 单页 6.3 s，100 页串行需 10 分钟          | 解析按文档调度          | 解析改为**页级并行**调度                    | 01 §5.1、§7.1 |


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


| spike 中的位置                                          | 迁往                                           | 说明                         |
| --------------------------------------------------- | -------------------------------------------- | -------------------------- |
| `probes/encoding.py` 的 `CJK_LATIN_MAP` 与 `repair()` | `app/modules/ingestion/parsers/normalize.py` | 索引侧与查询侧必须共用这一份             |
| `probes/heading.py` 的 `NUMBERING` / `CLAUSE_INLINE` | `app/modules/ingestion/chunkers/`            | 已按真实文档校准过的正则               |
| `probes/header_footer.py` 的行聚类算法                    | `app/modules/ingestion/parsers/layout.py`    | 替代原设计的固定带宽方案               |
| `ocr.py` 的坐标换算（像素 → pt）                             | `app/modules/ingestion/parsers/ocr.py`       | `scale = 72 / dpi`，容易写错的一处 |
| `check.py` 整体                                       | `backend/scripts/parse_check.py`             | 退出码已就绪，可直接接进 CI 做解析回归      |




### 待确认事项

不阻塞 M0；**需在 M1 之前有答复**。


| 事项            | 影响                                                 | 建议何时确认 |
| ------------- | -------------------------------------------------- | ------ |
| 首批目标行业具体是哪两个  | 内置 profile 模板优先级、评测集构建、`clause_mode` 默认值           | 立即     |
| 是否有文档密级要求     | 需在 `chunks` 加 `security_level` 并入检索过滤，现在加字段远比上线后便宜 | 立即     |
| 是否需要对接企业 SSO  | `identity` 模块的认证扩展点                                | M4 前   |
| 知识库之间是否需要资料复用 | 文档与知识库是否从一对多改为多对多                                  | M4 前   |
| 回答是否会被写入正式文件  | 引用快照与不可篡改审计的严格程度                                   | M4 前   |




### 仍存在的未知


| 未知                                   | 计划何时消除            |
| ------------------------------------ | ----------------- |
| OCR 输出在**表格**上的还原质量（本次样本的表格都在文本层文档里） | M1，补一份带表格的扫描件进体检集 |
| 中文 Embedding 模型在工业术语上的实际召回率          | M2，用评测集标定         |
| 低置信度 OCR 文本对检索质量的实际影响幅度              | M2，对比开关该阈值的评测结果   |


---



## 变更记录


| 日期         | 提交        | 内容                                      |
| ---------- | --------- | --------------------------------------- |
| 2026-07-29 | `f5b399b` | M0 工程骨架：后端身份/平台层、前端骨架、Compose、CI、Docker |
| 2026-07-28 | `bf9753d` | 进展与计划文档                                 |
| 2026-07-28 | `0d3e29b` | OCR 分支 + 页级并行 + 条款式分块                   |
| 2026-07-28 | `e62c5f2` | 字符规范化 + 页眉页脚算法修正                        |
| 2026-07-28 | `cd7e0b6` | 解析质量体检 spike                            |
| 2026-07-28 | `a2145d8` | 六篇设计文档                                  |


