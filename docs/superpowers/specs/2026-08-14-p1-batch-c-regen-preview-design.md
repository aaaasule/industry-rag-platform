# P1 批次 C · 重新生成 + 非 PDF 预览

> 状态：实现中  
> 日期：2026-08-14

## 范围

- `POST /messages/{id}/regenerate`：对会话**最后一条**助手消息（`completed` / `failed`）原地重跑检索+生成，SSE 事件与 completions 一致；不新建用户消息
- `GET /documents/{id}/pages`：返回解析后的 `page_no` / `plain_text` / `source`
- 文档详情与问答右栏：PDF 仍走 pdf.js + bbox；其余格式用正文预览，并按分块/引用滚动高亮（无 bbox）

## 非目标

PDF 式坐标高亮（DOCX/XLSX/PPTX）、消息分叉历史、Celery chord
