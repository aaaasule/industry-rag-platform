# M4 切片：用量仪表盘前端

> 状态：已实现（待开 PR）  
> 日期：2026-08-04  
> 前置：用量 API（#7）、配额（#9）、health（#8）已合入 main

## 1. 目标

管理员（`owner` / `admin`）在前端查看本租户 LLM 用量与成本，对齐 `docs/01` 七张图与 `docs/03` §3.6 三类接口，达到客户可演示质量。

## 2. 已确认决策

| 项 | 选择 |
| --- | --- |
| 优先级 | 本切片仅仪表盘；运营 UI（接入点/成员/审计）下一刀 |
| 图表范围 | A：七图 + summary/series/breakdown |
| 类型 | 先同步 OpenAPI → `openapi.gen.ts`，再写页面 |
| 演示质量 | 客户演示级（空态 / 加载 / 权限 / stale 标注） |
| M1/M3 遗留 | 不插队 |

## 3. 非目标

- 运营管理 UI、QPS/并发限流、`/usages/records`、按月分区
- hourlies 主键扩展 user/kb（本切片 breakdown 对明细表聚合，见 §5）
- 熔断事件标注点、成员「只看自己」用量视图

## 4. 页面与交互

- 路由：`/usages`；导航「用量」仅 admin/owner 可见
- 共享筛选：时间（24h / 7d / 30d / 自定义）、时区默认 `Asia/Shanghai`、可选模型与用途
- 粒度：跨度 ≤48h → `hour`，否则 `day`；>7 天禁用 hour
- 角标：`stale_until`、环比用服务端 `compare_previous`
- 依赖：`recharts`；风格跟随现有 Tailwind / brand

## 5. 薄后端补齐

| 能力 | 说明 |
| --- | --- |
| `SeriesPoint.latency_p95_ms` | 从 hourlies 汇总；日桶取桶内 max(p95) 作为近似 |
| `breakdown.dimension` ∈ `user` \| `knowledge_base` | 对 `llm_usages` 按时间窗聚合 Top-N；`label` 尽量解析显示名 |
| 接入点健康表 | 前端读已有 `GET /model-connections`，不新增接口 |

## 6. 七图映射

1. Token 堆叠面积 — series 汇总 prompt/completion  
2. 成本折线 + 配额水位 — series.cost + summary.quota  
3. 模型环形 — breakdown model/cost  
4. 用途柱状 — breakdown purpose  
5. 接入点健康 + P95 — connections + series group_by=connection_id  
6. 成功率折线 — series.success_rate  
7. Top 排行 — breakdown user \| knowledge_base（页内切换）

## 7. 验收

- 东八区近 7 天成本日桶与后台同口径抽一天一致  
- 粒度与参数正确；member 无菜单或友好 403  
- 无数据统一空态；`stale_until` 可见  
