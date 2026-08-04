# M4 切片：用量埋点 + 预聚合 + 查询 API

> 状态：已实现（待合并）  
> 日期：2026-07-30  
> 顺序：本切片完成后 → health 故障转移

## 1. 目标

- 迁移：`model_pricing`、`llm_usages`（不分区）、`llm_usage_hourlies`
- `UsageRecorder.record()` → Redis；Celery flush + 小时预聚合
- 埋点：chat / retrieval / ingestion
- `GET /usages/summary|series|breakdown`（admin+）

## 2. 已确认决策

| 项 | 选择 |
| --- | --- |
| 范围 | B：埋点+hourlies+三类 API；无前端、无 429 |
| 写入 | Redis 缓冲 → Celery flush |
| 成本 | `model_pricing` + 写入快照 |
| 查询/表 | admin+；usages 暂不分区 |
| 架构 | modelops 扩展（方案 1） |

## 3. 非目标

前端仪表盘、配额 429、`/usages/records`、按月分区、health 故障转移、user/kb breakdown（本切片 breakdown 仅 model/purpose/connection）

## 4. 数据与 Redis

- 表结构对齐 docs/02；`llm_usages` 无 PARTITION
- hourlies 主键：`connection_id` 用 nil UUID 表示「无接入点」
- Redis key：`irp:usage:buffer`（LIST）；可选 `irp:usage:hourlies_until` 存新鲜度

## 5. 任务

- `stats.flush_usages`：RPOP/批量取 → 定价 → insert
- `stats.aggregate_hourlies`：按未聚合窗口 UPSERT

## 6. API

见 docs/03 §3.6 精简版；timezone 必填（series/summary）。

## 7. 测试

flush 后明细可见；hourlies 聚合；admin 可查、member 403；record 失败不影响主流程。
