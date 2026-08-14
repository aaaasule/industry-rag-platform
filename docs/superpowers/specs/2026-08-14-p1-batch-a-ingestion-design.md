# P1 批次 A · 解析与摄取

> 状态：实现中  
> 日期：2026-08-14  
> 决策：页级并行取「文档内线程池，chord 后置」；非 PDF 仅可检索、预览仍暂不支持

## 范围

- DOCX / XLSX / PPTX / Markdown·TXT 解析 → 统一 `PageParse`
- PDF OCR：`ThreadPoolExecutor` 文档内并行；`IRP_PARSE_OCR_WORKERS`（默认 4）
- Redis 细粒度进度 + `GET /documents/{id}/events` SSE；列表仍轮询
- 上传 accept 扩展；Celery chord **不做**

## 非目标

非 PDF 预览、HTML 解析、100 页真实压测、chord 页级任务
