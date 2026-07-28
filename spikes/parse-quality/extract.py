"""把 PDF 读成 DocSnapshot。

与 render.py 一起，是整个 spike 中仅有的两处依赖 PyMuPDF 的地方。所有探针
都建立在这里产出的中间表示之上，与具体解析库解耦——这正是 04 文档里
"解析产出统一中间表示"那一步的最小验证。
"""

from __future__ import annotations

import pathlib

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.24 只暴露 fitz 这个模块名
    import fitz  # type: ignore[no-redef]

from probes.base import DocSnapshot, PageSnapshot, Span
from probes.text_layer import needs_ocr

_BOLD_FLAG = 1 << 4
_TEXT_BLOCK = 0


def load(
    path: pathlib.Path,
    max_pages: int | None = None,
    ocr_engine=None,
    ocr_page_limit: int | None = None,
) -> DocSnapshot:
    """读取文档；传入 ocr_engine 时，对判定为扫描页的页面回退到 OCR。

    回退产出的 PageSnapshot 与文本层结构完全一致，因此下游探针无需区分来源。
    """
    doc = fitz.open(path)
    try:
        limit = doc.page_count if max_pages is None else min(max_pages, doc.page_count)
        pages = _snapshot_pages(doc, limit, ocr_engine, ocr_page_limit)
        return DocSnapshot(
            path=str(path),
            file_size=path.stat().st_size,
            page_count=doc.page_count,
            encrypted=bool(doc.is_encrypted),
            outline=[(lv, title, page) for lv, title, page in doc.get_toc()],
            pages=pages,
        )
    finally:
        doc.close()


def _snapshot_pages(doc, limit: int, ocr_engine, ocr_page_limit: int | None) -> list[PageSnapshot]:
    pages: list[PageSnapshot] = []
    ocr_done = 0
    for i in range(limit):
        snapshot = _snapshot_page(doc[i])
        if ocr_engine and needs_ocr(snapshot):
            if ocr_page_limit is None or ocr_done < ocr_page_limit:
                snapshot = ocr_engine.run_page(doc[i])
                ocr_done += 1
        pages.append(snapshot)
    return pages


def _snapshot_page(page) -> PageSnapshot:
    spans = list(_iter_spans(page))
    return PageSnapshot(
        page_no=page.number + 1,
        width=page.rect.width,
        height=page.rect.height,
        char_count=sum(len(span.text.strip()) for span in spans),
        image_area_ratio=_image_area_ratio(page),
        spans=spans,
    )


def _iter_spans(page):
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != _TEXT_BLOCK:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if not span["text"].strip():
                    continue
                yield Span(
                    text=span["text"],
                    bbox=tuple(float(v) for v in span["bbox"]),
                    size=round(float(span["size"]), 1),
                    bold=_is_bold(span),
                )


def _is_bold(span) -> bool:
    return bool(span["flags"] & _BOLD_FLAG) or "bold" in span["font"].lower()


def _image_area_ratio(page) -> float:
    """图片覆盖面积占页面的比例，用于判定扫描页。

    重叠图片会被重复计入，因此结果偏大，最终截断到 1.0。对"这页是不是整页
    扫描件"这个二元判断来说，偏大不影响结论。
    """
    page_area = page.rect.width * page.rect.height
    if page_area <= 0:
        return 0.0
    covered = sum(
        max(0.0, info["bbox"][2] - info["bbox"][0])
        * max(0.0, info["bbox"][3] - info["bbox"][1])
        for info in page.get_image_info()
    )
    return min(covered / page_area, 1.0)
