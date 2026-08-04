# M5 切片 B：prompt + retrieval 接入 resolve

> 状态：实施中  
> 日期：2026-08-04  

## 1. 目标

chat / search 消费 `EffectiveProfile.prompt_overrides` 与 `retrieval_rules`。

## 2. 决策

| 项 | 选择 |
| --- | --- |
| 多 KB | 取 `kb_ids[0]`（与 usage 埋点一致） |
| prompt | `system` 非空则替换默认 `SYSTEM_PROMPT`，证据块仍拼接 |
| chat top_k / rerank | 来自 resolve；`rerank_enabled is None` 回退 env |
| `/search` | `top_k` 可空；未显式传 `options.rerank` 时走 profile→env |
| 非目标 | CRUD/UI、evaluate、拒答阈值进 profile |

## 3. 验收

- `build_messages` 支持 system override  
- chat 使用 profile `top_k`（如 process_industry=10）  
- search 未传 top_k 时从首个 KB resolve  
