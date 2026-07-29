# M3 引用溯源 — 实施计划

> **For agentic workers:** 按步骤顺序执行；每步完成后勾选。

**Branch:** `feat/m3-citation-trace`

## Task 1: 规格已落盘

- [x] `docs/superpowers/specs/2026-07-29-m3-citation-trace-design.md`
- [x] 本计划

## Task 2: chunks API

- [x] Schema `ChunkOut` + repo `list_chunks` + service + router
- [x] 测试：有文档时返回列表；跨租户 404

## Task 3: feedback

- [x] 迁移 `0004_message_feedbacks`
- [x] ORM + schemas + service upsert + router
- [x] 测试：赞/踩 upsert；非助手 422

## Task 4: MessageOut 增强

- [x] `document_title` / `used_citations` / `feedback`
- [x] list_messages 组装

## Task 5: PdfHighlightViewer

- [x] 安装 `react-pdf`
- [x] 共享组件 + bbox 缩放

## Task 6: 问答页

- [x] 右栏切换 + used_citations 置灰 + 反馈 UI

## Task 7: 文档详情页

- [x] 路由 + 双栏 + KbDetail 标题链接

## Task 8: 收尾

- [x] typecheck / 相关 pytest
- [x] 更新 `docs/07-progress.md`
- [ ] 用户本地验收后合并
