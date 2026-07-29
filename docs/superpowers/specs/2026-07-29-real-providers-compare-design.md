# 真实 Embedding / LLM / Rerank 与召回对比 — 设计说明

**日期**：2026-07-29  
**分支**：`feat/real-providers-compare`  
**状态**：已批准，实施中  
**依据**：用户确认 DeepSeek 聊天 + DashScope Embedding/Rerank；交付脚本对比 + 手工验收

---

## 1. 目标与非目标

### 目标

1. 运行时配置支持 **LLM / Embedding / Rerank 凭证与 base_url 分离**。
2. 接入：
   - LLM：DeepSeek `deepseek-v4-flash`（或 `deepseek-v4-pro`；API 不接受裸名 `deepseek-v4`）
   - Embedding：DashScope `text-embedding-v4`，`dimensions=1024`，批大小 ≤10
   - Rerank：DashScope `qwen3-rerank`，base 为 **`compatible-api`**（非 `compatible-mode`），路径 **`/reranks`**；真实 Embedding 下检索 **默认开启** rerank
3. 对已有 ready 文档 reingest 后，用固定 query 产出 Fake vs Real、RRF vs RRF+rerank 对比报告。
4. 手工问答验收并写入 `docs/07-progress.md`。

### 非目标

- 双索引并存 / 改 `Vector` 列宽
- pdf.js 高亮、反馈（M3）
- 把 API Key 提交进仓库

---

## 2. 配置

| 前缀字段 | 用途 | 示例 |
| --- | --- | --- |
| `IRP_LLM_*` | Chat | `openai_compatible` + DeepSeek base/key/model |
| `IRP_EMBEDDING_*` | 向量 | 独立 `BASE_URL`/`API_KEY`/`MODEL`/`DIM`/`BATCH_SIZE` |
| `IRP_RERANK_*` | 重排 | 独立 provider/base/key/model；缺省时可回退 Embedding 的 DashScope 凭证 |
| `IRP_RETRIEVAL_RERANK_DEFAULT` | 默认是否重排 | 真实 Embedding 时默认 `true`；Fake 默认 `false` |

密钥仅写入本地 `backend/.env`（已 gitignore）。`.env.example` 只含占位与注释。

---

## 3. 代码边界

- `platform/config.py`：新字段  
- `platform/llm/openai_compatible.py`：`dimensions`；rerank 路径 `/reranks`；可选兼容 `/rerank`  
- `platform/llm/factory.py`：三套 Client；`close_providers` 全关  
- `platform/deps.py`：`RerankDep`  
- `modules/retrieval/service.py`：接线重排，填 `scores.rerank` / `rerank_ms`  
- `ingestion`：embed 批大小取自 settings  
- `scripts/compare_retrieval.py`：对比报告  
- 测试：工厂/客户端单测用 httpx mock；检索 rerank 用 Fake 可测默认关

跨模块：检索只依赖 `RerankProvider` 协议，不直连 httpx。

---

## 4. 召回对比流程

1. （可选）Fake 下对固定 queries 调 search → `artifacts/retrieval-compare/fake.json`  
2. 切真实 `.env`，重启 API + worker  
3. reingest 验收文档 → `ready`  
4. Real + `rerank=false` / `true` 各跑一轮 → JSON  
5. 脚本输出 Markdown：chunk 重叠、排序变化、耗时  

---

## 5. 验收标准

- [ ] 真实 Embedding reingest 成功，维数 1024  
- [ ] `/search` 开启 rerank 时 `scores.rerank` 非空  
- [ ] DeepSeek SSE 问答可达 `done`  
- [ ] 对比报告文件生成  
- [ ] `07-progress` 已记录  

---

## 6. 风险

| 风险 | 缓解 |
| --- | --- |
| `deepseek-v4` 模型名无效 | 联调探测，必要时改官方可用名 |
| DashScope `/reranks` 与 `compatible-mode` 不兼容 | 可配置 path；必要时换 `compatible-api` base |
| 批 >10 失败 | `embedding_batch_size` 默认 10 |
| 密钥曾出现在聊天 | 提醒轮换；永不 commit |

---

## 7. 规格自检

- [x] 无 TBD 阻塞实现  
- [x] 与现有 1024 维 DDL 一致  
- [x] 非目标明确  
- [x] 无密钥写入规格正文  
