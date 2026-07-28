"""把解析出的坐标画回页面导出 PNG。

指标能告诉你坐标"合法"，但没法告诉你坐标"对不对"。只有把框画回原图用肉眼
看一眼，才能确认前端 pdf.js 的高亮会落在正确的位置上。这是验证 ADR-005
最直接的手段，也是这个 spike 里唯一无法自动化的一步。
"""

from __future__ import annotations

import pathlib

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore[no-redef]

SPAN_COLOR = (0.85, 0.15, 0.15)
BAND_COLOR = (0.15, 0.45, 0.85)
BAND_RATIO = 0.08


def render_overlay(
    path: pathlib.Path,
    out_dir: pathlib.Path,
    page_numbers: list[int],
    dpi: int = 110,
) -> list[pathlib.Path]:
    """在指定页上描出每个文本 span 的 bbox，并标出页眉页脚判定带。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[pathlib.Path] = []

    doc = fitz.open(path)
    try:
        for page_no in page_numbers:
            if not 1 <= page_no <= doc.page_count:
                continue
            page = doc[page_no - 1]
            _draw_bands(page)
            _draw_spans(page)
            target = out_dir / f"{path.stem}_p{page_no}.png"
            page.get_pixmap(dpi=dpi).save(target)
            written.append(target)
    finally:
        doc.close()
    return written


def _draw_spans(page) -> None:
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if span["text"].strip():
                    page.draw_rect(fitz.Rect(span["bbox"]), color=SPAN_COLOR, width=0.6)


def _draw_bands(page) -> None:
    band = page.rect.height * BAND_RATIO
    width = page.rect.width
    for rect in (
        fitz.Rect(0, 0, width, band),
        fitz.Rect(0, page.rect.height - band, width, page.rect.height),
    ):
        page.draw_rect(rect, color=BAND_COLOR, width=1.2, dashes="[3 3] 0")
