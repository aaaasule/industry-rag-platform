# M6 知识库运营与检索智能化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 四周落地文档启用/批量/审计、KB settings 对外暴露、多轮指代与可选查询扩展、三条行业模板与本地 golden。

**Architecture:** 检索继续 join `documents` 并增加 `enabled` 过滤。KB 覆盖继续走已有 `merge_chunk_rules` / `merge_retrieval_rules`，只把 `settings` 暴露给 PATCH/UI。查询理解放在 Chat/Retrieval 编排层，不改 RRF。

**Tech Stack:** FastAPI + Alembic + SQLAlchemy async + pytest；React + TanStack Query；`make openapi`。

**Spec:** `docs/superpowers/specs/2026-08-28-m6-knowledge-ops-retrieval-design.md`

## Global Constraints

- 单次 batch ≤ 50；跨库 document_id 一律 404
- 不改 RRF、不加公开相似度阈值 API
- 改 settings **不**自动 reingest
- CI 评测仍只跑 `golden.ci.jsonl`
- 审计 `record()` 失败不得拖垮主路径（已有 try/nested）
- 前端 OpenAPI 变更后执行 `make openapi`
- 提交信息用 conventional commits（feat/fix/test/docs）
- 每周一个 PR，不要把四周塞进一次 merge

---

## File map

| 路径 | 职责 |
| --- | --- |
| `backend/alembic/versions/20260828_0010_document_enabled.py` | `documents.enabled` |
| `backend/app/modules/knowledge/models.py` | Document.enabled |
| `backend/app/modules/knowledge/schemas.py` | DocumentOut/Update、Batch、KB settings |
| `backend/app/modules/knowledge/service.py` | PATCH/batch/audit/chunk_count |
| `backend/app/modules/knowledge/router.py` | 新路由 |
| `backend/app/modules/retrieval/repository.py` | enabled 过滤 |
| `backend/app/modules/profile/schemas.py` | `query_expand` |
| `backend/app/modules/chat/rewrite.py`（新建） | 指代消解提示与解析 |
| `backend/app/modules/retrieval/query_expand.py`（新建） | 扩展触发与二次融合 |
| `frontend/src/features/knowledge/*` | 文件表/配置/检索/日志 |
| `backend/scripts/seed.py` | 离散 overlap、流程词典 |
| `backend/evals/golden.discrete.jsonl` 等 | 本地评测 |
| `docs/07-progress.md` | W4 进度 |

---

### Task 1: documents.enabled 迁移与检索过滤

**Files:**
- Create: `backend/alembic/versions/20260828_0010_document_enabled.py`
- Modify: `backend/app/modules/knowledge/models.py`
- Modify: `backend/app/modules/knowledge/schemas.py`（`DocumentOut.enabled`）
- Modify: `backend/app/modules/retrieval/repository.py`
- Test: `backend/tests/test_knowledge_api.py`（或新建 `test_document_enabled.py`）

**Interfaces:**
- Produces: `Document.enabled: bool` default True；`DocumentOut.enabled: bool`
- Retrieval: `Document.enabled.is_(True)` 与现有 `deleted_at` / `status==ready` 并列

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_document_enabled.py` 用现有 `client` / `auth_headers` / fixture：创建 KB、上传或插入 ready 文档，将 `enabled=False`（测试可先直接 SQL，API 未就绪时本 task 只测检索 SQL——若 API 尚未存在，本 task 先测 repository：插入两 chunk 所属文档分别 enabled T/F，`vector_search` 只返回 enabled 的）。

更稳妥：本 task 只加列 + ORM + repository 过滤的 **单元/集成** 测试：用 session 插入 Document+Chunk，调用 `RetrievalRepository.vector_search`，disabled 文档的 chunk 不出现。

- [ ] **Step 2: 迁移**

`down_revision = "0009_profile_code_reuse"`。

```python
op.add_column(
    "documents",
    sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
)
```

downgrade: `op.drop_column("documents", "enabled")`。

- [ ] **Step 3: ORM + repository**

`Document.enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)`。

两处 search `where` 增加 `Document.enabled.is_(True)`。

- [ ] **Step 4: 跑测**

```bash
cd backend && uv run alembic upgrade head && uv run pytest tests/test_document_enabled.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**（仅在用户要求提交时执行）

```bash
git add backend/alembic/versions/20260828_0010_document_enabled.py \
  backend/app/modules/knowledge/models.py \
  backend/app/modules/retrieval/repository.py \
  backend/tests/test_document_enabled.py
git commit -m "$(cat <<'EOF'
feat(knowledge): 文档 enabled 列并在检索中排除禁用文件

EOF
)"
```

---

### Task 2: PATCH 文档、列表字段、审计 upload/delete

**Files:**
- Modify: `backend/app/modules/knowledge/schemas.py`
- Modify: `backend/app/modules/knowledge/service.py`
- Modify: `backend/app/modules/knowledge/router.py`
- Modify: `backend/app/modules/knowledge/repository.py`（list 带 chunk_count）
- Modify: `backend/app/modules/ingestion/tasks.py` 或文档失败落点（`ingest.fail` 审计）
- Test: `backend/tests/test_document_enabled.py`、`backend/tests/test_audit_logs.py`

**Interfaces:**
- `class DocumentUpdate(BaseModel): enabled: bool | None = None; metadata: dict[str, Any] | None = None`
- `PATCH /documents/{doc_id}` → `DocumentOut`
- `DocumentOut`: `enabled: bool`, `chunk_count: int = 0`, `metadata: dict`（来自 `meta`，序列化别名 `metadata`）
- `KnowledgeService.update_document(claims, doc_id, payload) -> DocumentOut`
- 审计：`document.upload` / `document.delete`

Pydantic：`DocumentOut` 对 ORM `meta` 用 `Field(validation_alias="meta", serialization_alias="metadata")` 或 `model_validate` 时手动填 `metadata=doc.meta`。推荐 service 层组装，避免 Declarative `metadata` 保留字坑。

- [ ] **Step 1: 失败测试**

- PATCH `enabled=false` 后 POST `/search` 不含该 `document_id`
- 再 PATCH `true` 后可命中
- register 后 audit 含 `document.upload`
- delete 后含 `document.delete`
- metadata 未知键 → 422 `metadata_invalid`

- [ ] **Step 2: 实现 PATCH + list chunk_count**

`list_documents`：`select Document.id, func.count(Chunk.id)` group by，或两次查询。软删文档不计入。

- [ ] **Step 3: ingest.fail**

在 parse/embed 将 `status=failed` 处调用 `AuditService.record(action="ingest.fail", ...)`。Worker 内注意 RLS/session；若 Worker 无用户，`actor_id=None`。

- [ ] **Step 4: pytest + `make openapi`**

- [ ] **Step 5: Commit** `feat(knowledge): 文档 PATCH 启用状态、元数据与上传删除审计`

---

### Task 3: 批量 delete / reingest

**Files:**
- Modify: `backend/app/modules/knowledge/schemas.py`
- Modify: `backend/app/modules/knowledge/service.py` / `router.py`
- Test: `backend/tests/test_document_batch.py`

**Interfaces:**
- `class DocumentBatchRequest(BaseModel): action: Literal["delete","reingest"]; document_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)`
- `class DocumentBatchResponse(BaseModel): accepted: int; job_ids: dict[str, uuid.UUID | None]`
- `POST /knowledge-bases/{kb_id}/documents/batch`
- 权限：`PERM_WRITE`
- 循环调用现有 `delete_document` / `reingest`；reingest 写 `document.reingest` 审计（可每条或一条 payload 含 ids）

- [ ] **Step 1: 测试**

- 2 个文档 batch delete → 均 `deleted_at` 非空
- 51 个 ids → 422
- 他库 uuid → 404，本库文档不被误删

- [ ] **Step 2: 实现**

- [ ] **Step 3: pytest**

- [ ] **Step 4: Commit** `feat(knowledge): 知识库文档批量删除与重新解析`

---

### Task 4: 前端文件列表（W1 UI）

**Files:**
- Modify: `frontend/src/features/knowledge/api.ts` / `hooks.ts`
- Modify: `frontend/src/features/knowledge/panels/KbFilesPanel.tsx`
- Modify: `frontend/src/features/knowledge/panels/KbLogsPanel.tsx`
- Test: `cd frontend && pnpm lint && pnpm typecheck`

**Interfaces:**
- `patchDocument(docId, { enabled?, metadata? })`
- `batchDocuments(kbId, { action, document_ids })`
- `DocumentItem.enabled`, `chunk_count`, `metadata`

- [ ] **Step 1:** 类型与 hooks
- [ ] **Step 2:** 表格 checkbox、顶栏「重新解析」「删除」、每行启用开关（调用 PATCH）
- [ ] **Step 3:** 分块数列；日志文案包含上传/删除
- [ ] **Step 4:** lint/typecheck
- [ ] **Step 5:** Commit `feat(frontend): 知识库文件批量操作与启用开关`

W1 PR：合 Task 1–4。

---

### Task 5: KB settings PATCH 与 effective 规则出站

**Files:**
- Modify: `backend/app/modules/knowledge/schemas.py`（`KnowledgeBaseUpdate.settings`, `KnowledgeBaseOut`）
- Modify: `backend/app/modules/knowledge/service.py` `update_knowledge_base` / `*_out`
- Modify: `backend/app/modules/profile/schemas.py` — `RetrievalRulesConfig.query_expand: bool = False`
- Test: `backend/tests/test_profile_resolve.py`（已有 merge）；新增 API 测 `test_kb_settings.py`

**Interfaces:**
- 白名单校验函数 `validate_kb_settings(raw: dict) -> dict`，非法键 → 422 `settings_invalid`
- `KnowledgeBaseOut.settings`
- `effective_chunk_rules: dict`、`effective_retrieval_rules: dict`（`model_dump`）
- 摄取路径已 `resolve_effective_profile`，确认 ingest 读 KB settings（已有则只补测试：PATCH settings 后 reingest 块参数变化）

- [ ] **Step 1: 测试** PATCH `{ "settings": { "chunk_rules": { "max_tokens": 256 } } }` GET KB 的 effective max_tokens=256；未知键 422
- [ ] **Step 2: 实现出站与校验**
- [ ] **Step 3: pytest + openapi**
- [ ] **Step 4: Commit** `feat(knowledge): 暴露 KB settings 覆盖切块与检索规则`

---

### Task 6: 配置页可编辑 + 检索测试对齐 effective

**Files:**
- Modify: `frontend/src/features/knowledge/api.ts`、`KbSettingsPanel.tsx`、`KbRetrievalPanel.tsx`、`hooks.ts`

**Interfaces:**
- `updateKnowledgeBase(id, { settings: { chunk_rules, retrieval_rules } })`
- 配置页滑条/数字框绑定 KB settings；保存提示重新解析
- 检索测试默认 topK/rerank 来自 `effective_retrieval_rules`；增加「查询扩展」checkbox（W3 接 `options.query_expand`，本 task 可先传 options 即使后端忽略）

- [ ] **Step 1–4:** 实现、lint/typecheck、commit `feat(frontend): 知识库配置页在线覆盖切块与召回`

W2 PR：Task 5–6。

---

### Task 7: 多轮指代消解

**Files:**
- Create: `backend/app/modules/chat/rewrite.py`
- Modify: `backend/app/modules/chat/service.py` `_stream_answer`
- Modify: `backend/app/platform/llm/fake.py`（可选：识别 system 含 `指代` 时返回夹具）
- Test: `backend/tests/test_chat_rewrite.py`

**Interfaces:**
- `async def resolve_query(llm: LLMProvider, *, history: list[tuple[str,str]], current: str) -> str`
- history 为 (role, content) 最近 4 条 completed；无历史则返回 `current`
- 提示：只输出一个完整问句。解析：取第一行，strip 引号，长度 1–2000
- `_stream_answer` 用改写结果作为 `self._retrieval.search(..., query=...)`
- SSE `retrieval.rewritten_query` 已存在

- [ ] **Step 1: 单测 FakeLLM** 历史提到「HYD-2201」，当前「它的检修周期？」→ 夹具返回含 HYD-2201 的句子
- [ ] **Step 2: 实现 rewrite + 接入 stream**
- [ ] **Step 3: pytest**
- [ ] **Step 4: Commit** `feat(chat): 多轮指代消解后再检索`

---

### Task 8: 自适应查询扩展

**Files:**
- Create: `backend/app/modules/retrieval/query_expand.py`
- Modify: `backend/app/modules/retrieval/service.py`、`base.py` `SearchOptions.query_expand: bool | None = None`
- Modify: `backend/app/modules/retrieval/router.py` 读 `options.query_expand`
- Modify: `backend/app/modules/chat/service.py` 传入 `effective.retrieval_rules.query_expand`
- Modify: `frontend/src/features/knowledge/panels/KbRetrievalPanel.tsx`
- Test: `backend/tests/test_query_expand.py`

**Interfaces:**
- `EXPAND_RRF_FLOOR = 0.016`
- `should_expand(*, enabled: bool, fused: list[tuple[str,float]]) -> bool`
- 扩展用 LLM 生成一条 query，第二次 vector+fulltext，三次列表 RRF（原 vec、原 ft、扩 vec、扩 ft 或两次 fused 再 fuse）—— **采用两次 `rrf_fuse` 的 id 列表再 fuse**，实现简单
- 失败则返回第一次结果

- [ ] **Step 1: 纯函数测 should_expand**
- [ ] **Step 2: 接入 search；Fake 扩展 query 固定**
- [ ] **Step 3: Playground checkbox**
- [ ] **Step 4: Commit** `feat(retrieval): 可选查询扩展与二次 RRF`

W3 PR：Task 7–8。前端检索区展示 rewritten_query。

---

### Task 9: 元数据抽屉（可与 W1 后半或 W2 并行）

**Files:**
- Modify: `KbFilesPanel.tsx` 或新建 `DocumentMetaDrawer.tsx`
- 使用当前 KB bound profile / GET KB 后 GET profiles 的 `metadata_schema`

空 schema：不展示编辑。有字段：保存走 PATCH metadata。

- [ ] **Commit** `feat(frontend): 按行业 schema 编辑文档元数据`

---

### Task 10: 行业种子与 golden（W4）

**Files:**
- Modify: `backend/scripts/seed.py`
- Create: `backend/evals/golden.discrete.jsonl`, `backend/evals/golden.process.jsonl`
- Modify: `docs/07-progress.md`、知识模块设计书「后续演进」可标注 M6 进行中
- Optional: Makefile `eval-discrete` 文档化，**不要**改 CI 阈值

离散：`overlap_tokens: 128`。流程：dictionary 增加 `GB/T`、`AQ/T`。

golden 格式对齐 `golden.ci.jsonl` / `evaluate.py`；若无真实 doc UUID，用注释说明需本地 seed 后填写，或复用 CI 文档结构各写 ≥10 条合成问句（expected_doc_ids 指向 seed_eval 文档则仅适合 CI 库——**行业文件允许先写 query + 标签占位，evaluate 无标签 exit 2 时：至少保证文件存在且 `evaluate.py --help` 文档说明如何填 UUID**）。

更可执行：从 `golden.ci.jsonl` 复制结构，行业文件在 README/progress 写「替换为真实 KB 的 document_id」。避免 CI 红。

- [ ] **Step 1: seed 变更 + 单测 clause/overlap 仍可区分**
- [ ] **Step 2: 两份 jsonl + progress**
- [ ] **Step 3: Commit** `docs: M6 行业模板与评测语料占位`

W4 PR：Task 9（若未合）+ Task 10。

---

## 建议验证命令（每 PR）

```bash
cd backend && uv run pytest tests/test_document_enabled.py tests/test_document_batch.py tests/test_kb_settings.py tests/test_chat_rewrite.py tests/test_query_expand.py tests/test_audit_logs.py tests/test_profile_resolve.py -q
make eval-ci
cd frontend && pnpm lint && pnpm typecheck
```

浏览器（W1/W2）：知识库文件表开关与批量；配置保存 settings；检索测试。

---

## Spec coverage

| Spec 节 | Task |
| --- | --- |
| 4.1 enabled + PATCH + chunk_count | 1, 2 |
| 4.2 batch | 3 |
| 4.3 audit | 2, 3 |
| 4.4 settings | 5, 6 |
| 4.5 rewrite/expand | 7, 8 |
| 5 前端 | 4, 6, 8, 9 |
| 6 行业 | 10 |
| 7 验收 | 各 PR 手工 + 上列 pytest |

## 不做（防范围蔓延）

RRF 权重、自动全库 reingest、图谱、SSO、HTML 解析、CI 绑定行业 golden 硬失败。
