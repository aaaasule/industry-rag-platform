# M5 切片 B Implementation Plan

> **For agentic workers:** 按任务顺序实施；完成后跑相关单测。

**Goal:** chat/search 接入 EffectiveProfile 的 prompt 与 retrieval 规则。

**Architecture:** 以 `kb_ids[0]` 调用已有 `resolve_effective_profile`；chat 检索前取 top_k/rerank 与 system override；search 请求缺省时同样填充。

**Tech Stack:** FastAPI, Pydantic, 既有 profile 模块

## Global Constraints

- 不改 evaluate / 前端配置 UI  
- 多 KB 只用首个  

---

### Task 1: prompts + profile helpers

- [ ] `build_messages(..., system_override=)`  
- [ ] `primary_kb_id` / `resolve_rerank` 辅助  

### Task 2: chat + search 接线

- [ ] `ChatService.stream_completion` 用 resolve  
- [ ] `SearchRequest.top_k` 可空；router 填充  

### Task 3: seed / tests / progress

- [ ] process_industry 种子 system 文案（可区分）  
- [ ] 单测 + progress  
