# M3 引用溯源 — 设计说明

**日期**：2026-07-29  
**分支**：`feat/m3-citation-trace`  
**状态**：已确认，实施中  
**依据**：用户确认标准 M3 核心 + 方案 A

---

## 1. 目标与非目标

### 目标

1. 问答页点 `[n]` / 证据卡片 → 右栏切到 PDF，按 `bboxes` 高亮（可切回证据列表）。
2. 文档详情页 `/knowledge/:kbId/documents/:docId`：左 PDF / 右分块，双向联动；支持 `?page=&chunk=`。
3. 助手消息 👍 直接提交；👎 可选原因后再提交。
4. `used_citations` 置灰未实际引用的证据。

### 非目标

| 项 | 延后 |
| --- | --- |
| 重新生成 | 后续 |
| XLSX / PPTX / Markdown 解析 | 后续 |
| 改检索算法 / `kb_grants` | M4+ |

---

## 2. 决策摘要

| 决策 | 选择 |
| --- | --- |
| 范围 | 标准 M3 核心 |
| 问答 PDF 布局 | 右栏替换证据列表 |
| 反馈 | 赞直接；踩带原因 |
| 详情入口 | 独立路由 + 问答可跳转带高亮 |
| 技术 | 共享 `PdfHighlightViewer`（react-pdf） |

---

## 3. 后端

### 3.1 `GET /documents/{doc_id}/chunks`

返回（按 `seq`）：

`id, seq, content(=raw_content), heading_path, page_start, page_end, bboxes, chunk_type`

权限与 `GET /documents/{doc_id}` 一致。

### 3.2 `POST /messages/{message_id}/feedback`

Body：`{ rating: "up"|"down", reason?: "irrelevant"|"bad_citation"|"other", comment?: string }`

- 仅 `role=assistant` 且 `status=completed` 可评
- 同一 `user_id + message_id` upsert
- 表 `message_feedbacks` + RLS；迁移 `0004`

### 3.3 历史消息增强

- `CitationOut.document_title`（列表时 join 文档标题）
- `MessageOut.used_citations`（自 `retrieval_meta.used_citations`）
- `MessageOut.feedback`（当前用户对该消息的评价，可空）

### 3.4 复用

`GET /documents/{id}/preview-url` 不变；MinIO 已开 CORS。

---

## 4. 前端

1. `components/PdfHighlightViewer`：`url / page / bboxes`；PDF 用户空间 pt，原点左上，缩放重算。
2. 问答右栏：`EvidencePanel` ⇄ PDF；「返回证据」；未用引用置灰。
3. `DocumentDetailPage`：列表标题链接；query 高亮。
4. `MessageFeedback`：👍/👎 + 踩原因弹层。

非 PDF：展示「暂不支持预览」文案，分块列表仍可用。

---

## 5. 验收

1. 点 `[1]` → 右栏 PDF 跳到正确页且高亮覆盖引用区域。
2. 文档详情：点分块 → 左栏跳页高亮；列表可进入。
3. 赞/踩落库；刷新后状态保留。
4. 未出现在 `used_citations` 的证据卡片置灰。
