"""PDF 文本层解析（PyMuPDF）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.ingestion.parsers.normalize import normalize

CHAR_THRESHOLD = 50
IMAGE_RATIO_THRESHOLD = 0.5
_TEXT_BLOCK = 0
_BOLD_FLAG = 1 << 4


@dataclass
class PageParse:
    page_no: int
    width: float
    height: float
    blocks: list[dict[str, Any]]
    plain_text: str
    source: str  # text | ocr
    needs_ocr: bool


def parse_pdf_bytes(data: bytes, *, max_pages: int | None = None) -> list[PageParse]:
    try:
        import pymupdf as fitz
    except ImportError:  # pragma: no cover
        import fitz  # type: ignore[no-redef]

    doc = fitz.open(stream=data, filetype="pdf")
    try:
        limit = doc.page_count if max_pages is None else min(max_pages, doc.page_count)
        return [_parse_page(doc[i]) for i in range(limit)]
    finally:
        doc.close()


def _parse_page(page: Any) -> PageParse:
    spans: list[dict[str, Any]] = []
    order = 0
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != _TEXT_BLOCK:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = normalize(span["text"])
                if not text.strip():
                    continue
                size = round(float(span["size"]), 1)
                bold = bool(span["flags"] & _BOLD_FLAG) or "bold" in span["font"].lower()
                spans.append(
                    {
                        "type": "paragraph",
                        "level": 0,
                        "text": text,
                        "bbox": [float(v) for v in span["bbox"]],
                        "order": order,
                        "size": size,
                        "bold": bold,
                    }
                )
                order += 1

    char_count = sum(len(s["text"].strip()) for s in spans)
    image_ratio = _image_area_ratio(page)
    needs = char_count < CHAR_THRESHOLD and image_ratio > IMAGE_RATIO_THRESHOLD
    plain = "".join(s["text"] for s in spans)
    return PageParse(
        page_no=page.number + 1,
        width=float(page.rect.width),
        height=float(page.rect.height),
        blocks=spans,
        plain_text=plain,
        source="text",
        needs_ocr=needs,
    )


def _image_area_ratio(page: Any) -> float:
    area = page.rect.width * page.rect.height
    if area <= 0:
        return 0.0
    covered = 0.0
    for info in page.get_image_info():
        x0, y0, x1, y1 = info["bbox"]
        covered += max(0.0, x1 - x0) * max(0.0, y1 - y0)
    return min(covered / area, 1.0)
