# M5 缺口与工程债 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐 metadata 校验、Profile 软删、jieba 行业词典，以及 CI 硬失败检索评测（Recall@10=1.0 / MRR=1.0），并更新进展文档。

**Architecture:** 纯函数校验挂在 `register_document`；`industry_profiles.deleted_at` + DELETE API；`parse_rules.dictionary` 经 `ensure_jieba_userdict` 注入 `build_tsv`（摄取与检索）；独立 Eval CI job：migrate → 起 API → `seed_eval_ci` → `evaluate.py --min-*`。

**Tech Stack:** FastAPI、SQLAlchemy/Alembic、jieba、httpx、GitHub Actions、pytest、React（ProfilesPanel 删除按钮）

**Spec:** `docs/superpowers/specs/2026-08-05-m5-gaps-engineering-debt-design.md`

## Global Constraints

- Profile 删除：软删；内置不可删；有未删 KB 引用 → 409 `profile_in_use`
- CI 阈值：Recall@10 ≥ 1.0 且 MRR ≥ 1.0；不达标 exit ≠ 0
- 术语表：仅 `dictionary: list[str]` + jieba userdict；不做同义词
- metadata：空 schema 放行；未知键拒绝；type ∈ {string,number,boolean}
- 分支建议：`feat/m5-gaps-debt`；按 Task 提交，可拆 PR-1（Task 1–5）/ PR-2（Task 6–8）/ PR-3（Task 9）

---

## File map

| 文件 | 职责 |
| --- | --- |
| `backend/app/modules/knowledge/metadata_validate.py` | `validate_document_metadata` |
| `backend/app/modules/ingestion/chunkers/dictionary.py` | `ensure_jieba_userdict` + 指纹缓存 |
| `backend/app/modules/ingestion/chunkers/tsv.py` | `build_tsv(..., dictionary=)` |
| `backend/alembic/versions/20260805_0008_profile_soft_delete.py` | `deleted_at` |
| `backend/scripts/seed_eval_ci.py` | CI 评测语料幂等 seed |
| `backend/evals/golden.ci.jsonl` | CI golden |
| `.github/workflows/ci.yml` | Eval job |
| `Makefile` | `eval-ci` target |
| `docs/07-progress.md` | 进度 |

---

### Task 1: metadata 校验纯函数 + 单测

**Files:**
- Create: `backend/app/modules/knowledge/metadata_validate.py`
- Create: `backend/tests/test_metadata_validate.py`

**Interfaces:**
- Produces: `validate_document_metadata(meta: dict[str, Any], schema: dict[str, Any]) -> None`；非法时 `raise UnprocessableState(..., code="metadata_invalid")`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_metadata_validate.py
import pytest
from app.modules.knowledge.metadata_validate import validate_document_metadata
from app.platform.errors import UnprocessableState

def test_empty_schema_allows_anything() -> None:
    validate_document_metadata({"x": 1}, {})

def test_rejects_unknown_key() -> None:
    schema = {"equipment_model": {"type": "string"}}
    with pytest.raises(UnprocessableState) as ei:
        validate_document_metadata({"equipment_model": "A", "extra": 1}, schema)
    assert ei.value.code == "metadata_invalid"

def test_required_missing() -> None:
    schema = {"equipment_model": {"type": "string", "required": True}}
    with pytest.raises(UnprocessableState):
        validate_document_metadata({}, schema)

def test_type_mismatch() -> None:
    schema = {"n": {"type": "number"}}
    with pytest.raises(UnprocessableState):
        validate_document_metadata({"n": "x"}, schema)

def test_valid_passes() -> None:
    schema = {
        "equipment_model": {"type": "string", "required": True},
        "flag": {"type": "boolean"},
    }
    validate_document_metadata({"equipment_model": "HYD-2201", "flag": True}, schema)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_metadata_validate.py -v`  
Expected: FAIL（模块不存在）

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/modules/knowledge/metadata_validate.py
from __future__ import annotations
from typing import Any
from app.platform.errors import UnprocessableState

_TYPE_CHECKERS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
}

def validate_document_metadata(meta: dict[str, Any], schema: dict[str, Any]) -> None:
    if not schema:
        return
    unknown = set(meta) - set(schema)
    if unknown:
        raise UnprocessableState(
            f"元数据含未声明字段: {', '.join(sorted(unknown))}",
            code="metadata_invalid",
        )
    for key, spec in schema.items():
        if not isinstance(spec, dict):
            continue
        required = bool(spec.get("required"))
        if key not in meta:
            if required:
                raise UnprocessableState(f"缺少必填元数据: {key}", code="metadata_invalid")
            continue
        typ = spec.get("type")
        checker = _TYPE_CHECKERS.get(typ) if isinstance(typ, str) else None
        if checker is not None and not checker(meta[key]):
            raise UnprocessableState(
                f"元数据字段 {key} 类型应为 {typ}",
                code="metadata_invalid",
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_metadata_validate.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/knowledge/metadata_validate.py backend/tests/test_metadata_validate.py
git commit -m "feat(knowledge): 文档 metadata schema 校验纯函数"
```

---

### Task 2: register_document 接入校验

**Files:**
- Modify: `backend/app/modules/knowledge/service.py`（`register_document`）
- Modify: `backend/tests/test_knowledge_api.py`（或新建 `test_document_metadata_api.py`）

**Interfaces:**
- Consumes: `validate_document_metadata`, `resolve_effective_profile(session, kb_id)`
- Produces: 登记时违反 schema → HTTP 422，`code=metadata_invalid`

- [ ] **Step 1: Write failing API test**

在 `backend/tests/test_document_metadata_api.py`：创建 KB，绑定带 `metadata_schema` 的 profile（或 PATCH KB settings），multipart/register 带未知键，断言 422。

可参考现有 upload 测试；最小路径：直接调 service 或 HTTP upload + metadata 若 API 支持。若 `DocumentRegisterRequest` / upload 暂无 metadata 字段，则：

1. 确认 `DocumentRegisterRequest.metadata` 已存在（schemas）；
2. 用 register JSON 端点测；或在 upload 后无法测时，对 service 做集成测：

```python
async def test_register_rejects_unknown_metadata(auth_headers, fixture_data, client):
    # 1) 派生 profile，metadata_schema={"equipment_model":{"type":"string","required":True}}
    # 2) 创建 KB 绑该 profile
    # 3) POST register 带 metadata={"wrong":1} → 422
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/test_document_metadata_api.py -v`  
Expected: FAIL（尚未校验）

- [ ] **Step 3: Wire into register_document**

在 `register_document` 创建 `Document` 之前：

```python
from app.modules.profile.service import resolve_effective_profile
from app.modules.knowledge.metadata_validate import validate_document_metadata

effective = await resolve_effective_profile(self._repo._session, kb.id)
validate_document_metadata(payload.metadata or {}, effective.metadata_schema)
```

- [ ] **Step 4: Run tests PASS**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(knowledge): 登记文档时校验 EffectiveProfile.metadata_schema"
```

---

### Task 3: Profile 软删除（迁移 + API + 测试）

**Files:**
- Create: `backend/alembic/versions/20260805_0008_profile_soft_delete.py`
- Modify: `backend/app/modules/knowledge/models.py` — `IndustryProfile.deleted_at`
- Modify: `backend/app/modules/knowledge/repository.py` — list/get 过滤 `deleted_at IS NULL`
- Modify: `backend/app/modules/knowledge/service.py` — `delete_profile`
- Modify: `backend/app/modules/knowledge/router.py` — `DELETE /industry-profiles/{profile_id}`
- Modify: `backend/app/modules/profile/service.py` — resolve 遇已删则回退
- Modify: `backend/tests/test_profile_crud.py`

**Interfaces:**
- Produces: `async def delete_profile(self, claims, profile_id) -> None`
- HTTP 204；422 `builtin_immutable`；409 `profile_in_use`；404

- [ ] **Step 1: Failing tests in test_profile_crud.py**

```python
async def test_delete_custom_profile(client, auth_headers, fixture_data):
    # POST derive → DELETE → GET 列表无该 id → 再 DELETE 404

async def test_cannot_delete_builtin(client, auth_headers):
    # GET 内置 id → DELETE → 422

async def test_cannot_delete_profile_in_use(client, auth_headers, fixture_data):
    # derive → 绑 KB → DELETE → 409 code profile_in_use
```

- [ ] **Step 2: Run FAIL**

- [ ] **Step 3: Migration**

```python
def upgrade() -> None:
    op.add_column(
        "industry_profiles",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("industry_profiles", "deleted_at")
```

ORM:

```python
deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

`list_profiles` / `get_profile` / `get_profile_by_code` 增加 `.where(IndustryProfile.deleted_at.is_(None))`（内置同样）。

`delete_profile`：

```python
async def delete_profile(self, claims: TokenClaims, profile_id: uuid.UUID) -> None:
    await self._require_admin(claims)  # 与 create/update 相同权限辅助
    row = await self._repo.get_profile(claims.tenant_id, profile_id)
    if row is None or row.deleted_at is not None:
        raise NotFound("行业模板不存在")
    if row.is_builtin or row.tenant_id is None:
        raise UnprocessableState("内置模板不可删除", code="builtin_immutable")
    in_use = await self._repo.count_kbs_with_profile(profile_id)  # 未删 KB
    if in_use:
        raise Conflict("仍有知识库绑定该模板", code="profile_in_use")
    row.deleted_at = datetime.now(UTC)
```

Router:

```python
@router.delete("/industry-profiles/{profile_id}", status_code=204)
async def delete_profile(...):
    await service.delete_profile(claims, profile_id)
```

resolve：若加载到的 profile `deleted_at` 非空，当作无 profile。

- [ ] **Step 4: migrate + pytest PASS**

Run: `uv run alembic upgrade head && uv run pytest tests/test_profile_crud.py -v`

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(profile): 行业模板软删除 API"
```

---

### Task 4: 前端删除按钮

**Files:**
- Modify: `frontend/src/features/profiles/api.ts` — `deleteProfile(id)`
- Modify: `frontend/src/features/profiles/hooks.ts` — `useDeleteProfile`
- Modify: `frontend/src/features/profiles/ProfilesPanel.tsx` — 自定义行删除 + confirm + toast

- [ ] **Step 1: api + hook**

```typescript
export async function deleteProfile(id: string): Promise<void> {
  await http.delete(`/industry-profiles/${id}`);
}
```

- [ ] **Step 2: UI** — 非 builtin 显示「删除」；`window.confirm`；409 时 `toast.error` 展示「仍有知识库绑定」

- [ ] **Step 3: typecheck**

Run: `cd frontend && pnpm typecheck && pnpm lint`

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(frontend): 行业模板软删除入口"
```

---

### Task 5: jieba userdict + seed + 摄取/检索接线

**Files:**
- Create: `backend/app/modules/ingestion/chunkers/dictionary.py`
- Modify: `backend/app/modules/ingestion/chunkers/tsv.py`
- Modify: `backend/app/modules/profile/schemas.py` — `ParseRulesConfig.dictionary: list[str] = []`
- Modify: `backend/app/modules/ingestion/tasks.py` — embed 路径 `build_tsv(..., dictionary=...)`
- Modify: `backend/app/modules/retrieval/` — 查询侧 `build_tsv` 调用处传 dictionary
- Modify: `backend/scripts/seed.py` — discrete 模板 `parse_rules.dictionary`
- Create: `backend/tests/test_jieba_userdict.py`

**Interfaces:**
- Produces: `ensure_jieba_userdict(words: Sequence[str]) -> None`
- Produces: `build_tsv(text: str, dictionary: Sequence[str] | None = None) -> str`
- Consumes: `effective.parse_rules` 中的 `dictionary` 列表（dict 用 `.get("dictionary")`）

- [ ] **Step 1: Failing test**

```python
from app.modules.ingestion.chunkers.tsv import build_tsv

def test_dictionary_keeps_compound_token() -> None:
    word = "液压缸座总成"
    tokens = build_tsv(word, dictionary=[word]).split()
    assert word in tokens
```

- [ ] **Step 2: Run FAIL**（无 dictionary 参数时词可能被切开）

- [ ] **Step 3: Implement dictionary.py + tsv.py**

```python
# dictionary.py
from __future__ import annotations
import hashlib
from collections.abc import Sequence

_fingerprint: str | None = None

def ensure_jieba_userdict(words: Sequence[str]) -> None:
    global _fingerprint
    cleaned = sorted({w.strip() for w in words if w and str(w).strip()})
    if not cleaned:
        return
    fp = hashlib.sha256("\n".join(cleaned).encode()).hexdigest()
    if fp == _fingerprint:
        return
    import jieba
    import tempfile, os
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
        for w in cleaned:
            f.write(f"{w}\n")
        path = f.name
    try:
        jieba.load_userdict(path)
    finally:
        os.unlink(path)
    _fingerprint = fp
```

```python
# tsv.py
def build_tsv(text: str, dictionary: Sequence[str] | None = None) -> str:
    try:
        import jieba
    except ImportError:
        return text
    if dictionary:
        from app.modules.ingestion.chunkers.dictionary import ensure_jieba_userdict
        ensure_jieba_userdict(dictionary)
    tokens = jieba.lcut_for_search(text)
    return " ".join(t for t in tokens if t.strip())
```

Wire ingestion `build_tsv(draft.content)` → 传入 `effective` 的 dictionary。  
Wire retrieval query tokenization 同样传入。

Seed discrete:

```python
"parse_rules": {"dictionary": ["液压缸座总成", "HYD-2201"]},
```

- [ ] **Step 4: pytest PASS**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(ingestion): parse_rules.dictionary 驱动 jieba userdict"
```

---

### Task 6: evaluate 阈值门禁 + `_relevant_rank` 单测

**Files:**
- Modify: `backend/scripts/evaluate.py`
- Create: `backend/tests/test_evaluate_metrics.py`（把 `_relevant_rank` 抽到可 import 模块，或 `from scripts.evaluate import` 若 path 允许）

建议：将 `_relevant_rank` 移到 `backend/app/modules/retrieval/eval_metrics.py` 供脚本与测试共用。

- [ ] **Step 1: 抽出 `_relevant_rank` + 单测**

```python
def test_relevant_rank_by_id():
    hits = [{"document_id": "a"}, {"document_id": "b"}]
    assert relevant_rank(hits, {"expected_document_ids": ["b"]}) == 2
```

- [ ] **Step 2: evaluate.py 增加参数**

```python
p.add_argument("--min-recall", type=float, default=None)
p.add_argument("--min-mrr", type=float, default=None)
# main 末尾：
if n == 0:
    print("无带标签样本", file=sys.stderr)
    return 2
recall = sum(recalls) / n
mrr = sum(rr_list) / n
if args.min_recall is not None and recall < args.min_recall:
    return 1
if args.min_mrr is not None and mrr < args.min_mrr:
    return 1
return 0
```

注意：当前 empty golden `return 0` 改为对 CI 不友好——**无标签样本必须 return 2**。

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(eval): evaluate 支持 min-recall/min-mrr 硬门槛"
```

---

### Task 7: CI seed + golden.ci.jsonl

**Files:**
- Create: `backend/scripts/seed_eval_ci.py`
- Create: `backend/evals/golden.ci.jsonl`

**固定 UUID（写入脚本常量，golden 引用）：**

```text
TENANT_SLUG=eval-ci
EMAIL=eval-ci@example.com
PASSWORD=EvalCI-Passw0rd!
KB_ID=01900000-0000-7000-8000-000000000001
DOC_ID=01900000-0000-7000-8000-000000000002
CHUNK 文本含独特句：EVAL_CI_MARKER_HYD2201_保养周期为三个月
```

- [ ] **Step 1: seed_eval_ci.py**

幂等：存在则跳过创建。写入 tenant/user/membership、profile（可用 general）、KB、Document(`ready`)、Chunk（embedding 用 `FakeEmbeddingProvider().embed` 同步或预计算 1024 维；tsv 用 `build_tsv`）。

因 Fake Embedding 确定性，query=`EVAL_CI_MARKER_HYD2201 保养周期` 应能命中。

- [ ] **Step 2: golden.ci.jsonl**

```json
{"query":"EVAL_CI_MARKER_HYD2201 保养周期","kb_id":"01900000-0000-7000-8000-000000000001","expected_document_ids":["01900000-0000-7000-8000-000000000002"]}
```

- [ ] **Step 3: 本地手跑**

```bash
# API 已起、migrate 后
cd backend && uv run python -m scripts.seed_eval_ci
uv run python scripts/evaluate.py --base http://127.0.0.1:8000/api/v1 \
  --email eval-ci@example.com --password 'EvalCI-Passw0rd!' --tenant eval-ci \
  --kb-id 01900000-0000-7000-8000-000000000001 \
  --golden evals/golden.ci.jsonl --k 10 --min-recall 1.0 --min-mrr 1.0
```

Expected: exit 0，recall/mrr = 1.0

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(eval): CI 专用 seed 与 golden.ci.jsonl"
```

---

### Task 8: CI Eval job + Makefile

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `Makefile`

- [ ] **Step 1: 增加 `eval` job**

`needs: []` 可与 backend 并行，但需自带 postgres/redis（复制 backend services/env）。步骤：

1. uv sync  
2. init role + migrate  
3. 后台 `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`  
4. wait-for-http `http://127.0.0.1:8000/healthz`  
5. `uv run python -m scripts.seed_eval_ci`  
6. `uv run python scripts/evaluate.py ... --min-recall 1.0 --min-mrr 1.0`  

`IRP_EMBEDDING_PROVIDER=fake` 等与 backend job 一致。

- [ ] **Step 2: Makefile**

```makefile
.PHONY: eval-ci
eval-ci: ## 对已启动的 API 跑 CI 同款评测硬门槛
	cd backend && uv run python -m scripts.seed_eval_ci && \
	uv run python scripts/evaluate.py --base http://127.0.0.1:8000/api/v1 \
	  --email eval-ci@example.com --password 'EvalCI-Passw0rd!' --tenant eval-ci \
	  --kb-id 01900000-0000-7000-8000-000000000001 \
	  --golden evals/golden.ci.jsonl --k 10 --min-recall 1.0 --min-mrr 1.0
```

- [ ] **Step 3: Commit**

```bash
git commit -m "ci: 检索评测硬失败 job（Recall@10/MRR=1.0）"
```

---

### Task 9: 进展文档（+ 可选 OpenAPI）

**Files:**
- Modify: `docs/07-progress.md`
- Optional: 跑 `uv run python -m scripts.export_openapi frontend/src/types/openapi.json` 并提交若有 DELETE/POST 漂移

- [ ] **Step 1: 更新当前状态表** — 阶段改为 **M5 缺口收口**；下一里程碑按实填写

- [ ] **Step 2: 追加完成记录** — metadata / 软删 / dictionary / CI eval

- [ ] **Step 3: Commit**

```bash
git commit -m "docs: 记录 M5 缺口与工程债收尾"
```

---

## Spec coverage check

| Spec 项 | Task |
| --- | --- |
| M-1 metadata 校验 | 1–2 |
| M-2 软删 | 3–4 |
| M-3/M-4 dictionary + seed | 5 |
| M-5 测试 | 分散在 1–5 |
| E-1–E-5 CI eval | 6–8 |
| D-1 progress | 9 |
| D-2 OpenAPI 可选 | 9 |

## Placeholder scan

无 TBD；阈值与固定 UUID 已写死。

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-05-m5-gaps-engineering-debt.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — 每个 Task 派生子代理，任务间审查  
2. **Inline Execution** — 本会话按 executing-plans 连续执行并设检查点  

**Which approach?**
