# M4 切片：QPS / 并发限流

> 状态：实施中  
> 日期：2026-08-04  
> 前置：配额 429、运营 UI、mypy chore (#12) 已合入

## 1. 目标

应用层 Redis 限流，超限返回 `429` + `rate_limited` + `Retry-After`。

## 2. 已确认决策

| 项 | 选择 |
| --- | --- |
| 挂载 | A：chat = QPS+并发；search = 仅 QPS |
| 并发占用 | A：进站至 SSE 流结束（含异常/取消） |
| Redis 故障 | 打日志并放行 |
| 关闭开关 | 对应 limit ≤0 关闭该项 |

## 3. 默认值（Settings / env）

| 配置 | 默认 | env |
| --- | --- | --- |
| 单用户每分钟 | 20 | `IRP_RATE_LIMIT_USER_PER_MINUTE` |
| 租户 chat 并发 | 10 | `IRP_RATE_LIMIT_TENANT_CHAT_CONCURRENCY` |

## 4. Redis

- QPS：`irp:rl:qps:{tenant_id}:{user_id}:{route}` ZSET 滑动窗口 60s  
- 并发：`irp:rl:inflight:{tenant_id}:chat` 计数；lease key `irp:rl:lease:{tenant_id}:{lease_id}` TTL 兜底防泄漏

## 5. 非目标

上传日限额、Nginx 限流、前端专门处理页、search 并发。
