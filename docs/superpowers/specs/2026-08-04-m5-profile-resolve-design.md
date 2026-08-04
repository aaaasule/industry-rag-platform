# M5 切片：EffectiveProfile + resolve + 分块接入

> 状态：实施中  
> 日期：2026-08-04  

## 1. 目标

四级配置回退的统一解析，摄取分块改走 `resolve(kb_id)`。

## 2. 已确认决策

| 项 | 选择 |
| --- | --- |
| 范围 | A：resolve + 分块；无 CRUD/前端/prompt/eval |
| 模块 | `app/modules/profile/` |
| 合并 | jsonb 域浅合并：KB.settings → profile → DEFAULT |

## 3. 非目标（切片 A）

POST/PATCH profile、配置 UI、evaluate.py。  
prompt/retrieval 接入见切片 B：`2026-08-04-m5-prompt-retrieval-design.md`。

## 4. 验收

- resolve 单测覆盖合并优先级  
- general vs process_industry（clause_mode）分块可区分  
