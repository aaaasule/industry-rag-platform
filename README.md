# industry-rag-platform

面向多行业的工业知识库平台。把企业内部散落的设备手册、工艺规程、维修工单、安全规范变成可用自然语言检索、且每句回答都能追溯到原文页面与位置的知识资产。

## 核心特性

- **多租户 + 行业可配置**：解析规则、分块策略、提示词、元数据 schema 全部由行业 profile 驱动，新增行业不改代码
- **引用溯源到坐标**：回答中的每个 `[n]` 都可点击跳转到原文页面并高亮对应区域
- **混合检索**：向量检索处理语义化提问，全文检索精确命中型号、标准号、错误码，RRF 融合
- **敢拒答**：无有效证据时明确拒答并引导补充资料，而不是编造

## 技术栈

后端 Python 3.11 + FastAPI + SQLAlchemy 2.0 + Celery，存储 PostgreSQL 16 + pgvector + S3 兼容对象存储，前端 React 18 + TypeScript + Vite + TanStack Query + Tailwind。

## 本地启动（M0）

前置：Docker、[uv](https://docs.astral.sh/uv/)、[pnpm](https://pnpm.io/)。

```bash
make bootstrap   # 起依赖 → 装包 → 迁移 → 种子数据 → 导出 OpenAPI 类型
make api         # http://localhost:8000  文档 /docs
make web         # http://localhost:5173
```

种子账号（口令均为 `Passw0rd!2026`）：

| 邮箱 | 租户 | 角色 |
| --- | --- | --- |
| `owner@acme.example` | 艾克姆装备制造（兼北方化工） | owner / member |
| `admin@acme.example` | 艾克姆装备制造 | admin |
| `owner@northchem.example` | 北方化工 | owner |

常用命令见 `make help`。

## 项目状态

**M0–M5 与 P1（A→D）已完成**；**真实行业语料 E2E 验收已通过**（2026-08-26）。下一里程碑 **M6 待定**。进度见 [07 进展与计划](./docs/07-progress.md)，设计文档见 [`docs/`](./docs/README.md)。

| 文档 | 内容 |
| --- | --- |
| [01 架构设计](./docs/01-architecture.md) | 目标与范围、总体架构、模块划分、技术选型、ADR |
| [02 数据模型](./docs/02-data-model.md) | ER 模型、DDL、多租户隔离、索引策略 |
| [03 API 设计](./docs/03-api.md) | 接口约定、端点清单、SSE 事件流、前端映射 |
| [04 RAG 流水线](./docs/04-rag-pipeline.md) | 解析、分块、检索、生成、评测、排查手册 |
| [05 部署与运维](./docs/05-deployment.md) | 仓库结构、编排、可观测性、容量与成本 |
| [06 路线图](./docs/06-roadmap.md) | 里程碑拆解、验收标准、风险登记表 |
| [07 进展与计划](./docs/07-progress.md) | 已完成工作、实测结论、下一步任务表 |

## License

见 [LICENSE](./LICENSE)。
