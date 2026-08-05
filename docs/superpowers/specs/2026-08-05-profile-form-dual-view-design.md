# 行业模板表单 + JSON 双视图

> 状态：已批准  
> 日期：2026-08-05  

## 0. 决策

| 项 | 选择 |
| --- | --- |
| 表单字段 | 常用：name + chunk_* + retrieval top_k/rerank + prompt.system |
| 同步 | Tab 切换双向合并；未知键保留 |
| 范围 | 仅自定义 profile 编辑；派生仍只 code/name |
| 后端 | 不改 API，沿用 PATCH |

## 1. 非目标

删除、派生全表单、parse/metadata 结构化控件、分栏实时双显。

## 2. 验收

- 表单改 top_k/clause_mode/system 可保存再读  
- JSON 改 parse_rules 后切表单再保存不丢  
- 非法 JSON 不可切回表单并提示  
