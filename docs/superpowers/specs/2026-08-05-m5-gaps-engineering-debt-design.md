# M5 缺口与工程债设计

> 状态：已批准  
> 日期：2026-08-05  
> 前置：M5 A–D 已合入（resolve / CRUD / 双视图 / evaluate 脚本）；视觉与 httpx 修复已进 main

## 0. 已确认决策

| 项 | 选择 |
| --- | --- |
| evaluate CI | **硬失败**阻断 Backend（或独立 Eval job 失败即失败 workflow） |
| CI 语料 | 专用 seed + `evals/golden.ci.jsonl`（Fake Embedding，可复现） |
| 硬失败阈值 | Recall@10 ≥ **1.0** 且 MRR ≥ **1.0** |
| Profile 删除 | **软删除** `deleted_at`；内置不可删；有 KB 引用 → **409** |
| 术语表 | `parse_rules.dictionary` → jieba `load_userdict`（索引/查询一致）+ seed 样例词 |
| 元数据 | 文档登记时按 EffectiveProfile.`metadata_schema` 校验；空 schema 放行；**拒绝未知键** |
| 落地形态 | 单主干分支，拆 **2～3 个小 PR** |
| 同义词归一 | **本轮不做** |
| Profile soft-delete 恢复 UI | **本轮不做**（仅删除 + 列表过滤） |

---

## 1. 目标

补齐 `docs/06-roadmap.md` M5 仍缺项与相关工程债，使：

1. 文档登记遵守行业 metadata schema；
2. 自定义行业模板可软删且不被误用；
3. 分词加载行业词典，型号类词不易被切碎；
4. CI 每次跑可复现检索评测，不达阈值则红；
5. `docs/07-progress.md` 反映真实进度。

## 2. 非目标

- 术语同义词改写（「泵浦」→「泵」）
- 术语表上传 API / 文件管理 UI
- Profile 恢复、审计时间线 UI
- 元数据 schema 可视化表单（仍可通过 Profile JSON / 双视图编辑 schema）
- 相对基线（2pp）门禁、按 commit 归档历史报告（可后置）
- 独立向量库 / 重排常态化 / 知识图谱等 M5 后演进项

---

## 3. 切片划分（PR）

### PR-1 · 运行时能力（校验 / 软删 / 词典）

| # | 交付 | 要点 |
| --- | --- | --- |
| M-1 | metadata 校验 | `validate_document_metadata(meta, schema)`；挂 `register_document`；422 |
| M-2 | Profile 软删 | Alembic：`industry_profiles.deleted_at`；`DELETE` API；列表/resolve 排除已删 |
| M-3 | jieba userdict | `parse_rules.dictionary: string[]`；`ensure_jieba_userdict`；`build_tsv` 接受可选词典 |
| M-4 | seed 样例 | 离散制造模板写入少量型号/设备词 |
| M-5 | 测试 | CRUD 删 / 引用冲突；metadata 合法/缺字段/多余键；分词不被切碎 |

### PR-2 · CI 硬失败评测

| # | 交付 | 要点 |
| --- | --- | --- |
| E-1 | CI seed 脚本 | 幂等写入评测租户 / KB / 文档 / chunk（固定 UUID 或稳定 code） |
| E-2 | `evals/golden.ci.jsonl` | 指向 CI seed；可用 `expected_document_ids` |
| E-3 | `evaluate.py` | 支持 `--min-recall` / `--min-mrr`（默认 1.0）；不达标 exit ≠ 0 |
| E-4 | CI 接线 | Backend job（或独立 Eval job，需同 workflow 失败策略）起 API → seed → evaluate |
| E-5 | Makefile | `make eval-ci` 本地对齐 |

### PR-3 · 文档与契约（可与 PR-2 合并）

| # | 交付 | 要点 |
| --- | --- | --- |
| D-1 | `docs/07-progress.md` | 当前状态改为 M5 缺口收尾；追加本节完成记录 |
| D-2 | OpenAPI 重导（可选） | 补 POST/PATCH/DELETE profiles，减少前端手写漂移 |

**推荐顺序**：PR-1 → PR-2 → PR-3（或 PR-3 并入 PR-2）。

---

## 4. 详细设计

### 4.1 Metadata schema 校验

**位置**：`app/modules/knowledge/` 或 `app/modules/profile/` 下纯函数，由 `KnowledgeService.register_document` 调用。

**规则**（与 `docs/03-api.md` 对齐的最小集）：

- `schema` 为空或 `{}` → 不校验，原样写入；
- `schema` 为「字段名 → `{ type, required? }`」对象：
  - `required: true` 且缺失 → 422 `metadata_invalid`；
  - `type` 支持 `string` / `number` / `boolean`（与现有 seed 一致）；类型不符 → 422；
  - **meta 中出现 schema 未声明的键 → 422**（拒绝未知字段）；
- 不在本轮做 `$ref` / 嵌套 object / array 复杂 JSON Schema。

**Effective schema 来源**：`resolve_effective_profile(session, kb_id).metadata_schema`。

### 4.2 Profile 软删除

**迁移**：`industry_profiles.deleted_at timestamptz NULL`。

**`DELETE /industry-profiles/{id}`**（admin+）：

| 条件 | 结果 |
| --- | --- |
| 不存在或跨租户或已删 | 404 |
| `is_builtin` | 422 `builtin_immutable` |
| 仍有未删 KB `profile_id = id` | 409 `profile_in_use` |
| 否则 | 设 `deleted_at = now()`，204 |

**读路径**：

- `GET /industry-profiles`：排除 `deleted_at IS NOT NULL`；
- `resolve()`：若命中已删自定义 profile，视为缺失并回退（与「无 profile」同级），避免绑定时已删却仍生效——**绑定检查已阻止删除，正常路径不应出现**；防御性回退仍建议保留。

**前端**：`ProfilesPanel` 自定义行增加「删除」+ 确认；toast 成功/409 提示。

### 4.3 术语表（jieba userdict）

**数据**：`parse_rules.dictionary: list[str]`（词条列表，非文件路径；避免 CI/多 worker 文件同步问题）。

**加载**：

```text
ensure_jieba_userdict(words: Sequence[str]) -> None
```

- 进程内按「规范化后的词表指纹」缓存，避免每 chunk 重复 `load_userdict`；
- 空列表 no-op。

**调用点**：

- 摄取写 chunk：`build_tsv(text, dictionary=effective.parse_rules.dictionary)`；
- 检索查询侧：构造全文查询前同样 `build_tsv` / 分词路径加载同一词典（与 `docs/02`「索引侧与查询侧一致」对齐）。

**Seed**：`discrete_manufacturing`（或现有离散模板）写入若干工业词（如型号片段），并加单测断言切词结果包含整词。

### 4.4 CI Evaluate 硬失败

**流水线（Backend 服务已具备 Postgres/Redis 的前提下）**：

1. migrate +（如需）角色初始化  
2. 启动 API（Fake Embedding / Fake 或现有 CI 模型配置，须与 seed 向量维度一致）  
3. 跑 `scripts/seed_eval_ci.py`（或 `seed.py --eval-ci` 标志）：写入固定租户/KB/文档/chunk  
4. `uv run python scripts/evaluate.py ... --golden evals/golden.ci.jsonl --k 10 --min-recall 1.0 --min-mrr 1.0`  
5. exit code ≠ 0 → job 失败 → PR 不可合（无 admin 绕过约定）

**`golden.ci.jsonl`**：进 git；只用 CI seed 的稳定 id/title；禁止依赖 `golden.local.jsonl`。

**本地**：`make eval-ci` 复现同一步骤（文档写明依赖 `make up` + API）。

**风险**：Fake Embedding 语义弱——CI 语料须「查询词与 chunk 文本有足够字面/向量重叠」以保证 1.0 稳定；seed 时应用确定性向量或保证全文能召回。

### 4.5 进展文档

更新 `docs/07-progress.md`：

- 「当前状态」→ M5 缺口收尾（或完成后「M5 收口」）；
- 追加 2026-08-05 完成表（校验 / 软删 / 词典 / CI eval）。

---

## 5. 测试计划

| 区域 | 用例 |
| --- | --- |
| metadata | 空 schema 放行；required 缺失 422；类型错 422；未知键 422；合法通过 |
| DELETE | 自定义软删成功；内置 422；在用 409；列表不再出现；再次 DELETE 404 |
| dictionary | 加载后整词保留；空词典行为与今一致 |
| evaluate | `_relevant_rank` 单测；CI 脚本在本地/`act` 或 CI 绿灯；故意改坏 golden 应红 |

---

## 6. 验收标准

- [ ] 登记文档违反 schema → 422，且错误码稳定可测  
- [ ] 自定义 profile 可软删；内置不可删；被 KB 引用不可删  
- [ ] seed 词典使样例工业词在 `build_tsv` 中保持完整  
- [ ] main 上 Backend/Eval CI：evaluate 不达 Recall@10=1.0 或 MRR=1.0 则失败  
- [ ] `07-progress.md` 与事实一致  

---

## 7. 开放问题（实施中可微调，不阻断开工）

1. Eval 作为 Backend job 末步 vs 独立 `Eval` job（需 `needs: backend`）——倾向独立 job 便于日志，但失败必须 fail-workflow。  
2. OpenAPI 重导是否并入 PR-3——有时间则做，无则记入债。  

---

## 8. 自检

- [x] 无 TBD/占位实现描述  
- [x] 与既有 C/D「不做删除/不做 CI」决策显式**覆盖**（本 spec 升级之）  
- [x] 软删与「绑定则 409」不矛盾  
- [x] 阈值 1.0 仅在可控 CI seed 下成立，已写明 Fake Embedding 风险  
- [x] 范围未混入同义词 / 图谱等  
