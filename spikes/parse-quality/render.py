"""把中间表示里的坐标画回页面导出 PNG。

指标能告诉你坐标"合法"，但没法告诉你坐标"对不对"。只有把框画回原图用肉眼
看一眼，才能确认前端 pdf.js 的高亮会落在正确的位置上。这是验证 ADR-005
最直接的手段，也是这个 spike 里唯一无法自动化的一步。

画的是 DocSnapshot 里的 span 而非重新提取，因此 OCR 页与文本层页走完全相同
的代码路径——OCR 坐标是否可靠，看到的就是最终会存进 chunks.bboxes 的东西。
"""

from __future__ import annotations

import pathlib

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore[no-redef]

from probes.base import DocSnapshot, PageSnapshot

TEXT_COLOR = (0.85, 0.15, 0.15)   # 文本层来源：红
OCR_COLOR = (0.10, 0.60, 0.25)    # OCR 来源：绿
LOW_CONF_COLOR = (0.95, 0.55, 0.0)  # 低置信度 OCR：橙
LOW_CONFIDENCE = 0.80


def render_overlay(
    doc_snapshot: DocSnapshot,
    out_dir: pathlib.Path,
    page_numbers: list[int],
    dpi: int = 110,
) -> list[pathlib.Path]:
    path = pathlib.Path(doc_snapshot.path)
    by_number = {p.page_no: p for p in doc_snapshot.pages}
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[pathlib.Path] = []

    doc = fitz.open(path)
    try:
        for page_no in page_numbers:
            snapshot = by_number.get(page_no)
            if snapshot is None:
                continue
            page = doc[page_no - 1]
            _draw_spans(page, snapshot)
            target = out_dir / f"{path.stem}_p{page_no}.png"
            page.get_pixmap(dpi=dpi).save(target)
            written.append(target)
    finally:
        doc.close()
    return written


def _draw_spans(page, snapshot: PageSnapshot) -> None:
    for span in snapshot.spans:
        page.draw_rect(fitz.Rect(span.bbox), color=_color(span, snapshot), width=0.6)


def _color(span, snapshot: PageSnapshot):
    if snapshot.source != "ocr":
        return TEXT_COLOR
    if span.confidence is not None and span.confidence < LOW_CONFIDENCE:
        return LOW_CONF_COLOR
    return OCR_COLOR
