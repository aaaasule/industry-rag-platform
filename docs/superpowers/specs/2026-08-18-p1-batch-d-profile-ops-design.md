# P1 批次 D · Profile 运营补齐 + 术语归一

> 状态：实现中  
> 日期：2026-08-18

## 范围

- `parse_rules.synonyms: {别名: 规范词}`，检索/问答查询侧最长匹配替换；不改索引、不重摄取
- Profile 表单：术语表（一行一词）、同义词行编辑、`metadata_schema` 字段表（key / type / required）；JSON 视图保留
- `GET /industry-profiles?include_deleted=` + `POST /industry-profiles/{id}/restore`；code 被占用 → 409 `profile_code_in_use`

## 非目标

LLM 查询改写、多轮指代消解、术语文件上传、索引侧同义词
