"""解析器共用：占位页与块构造。"""

from __future__ import annotations

from typing import Any

from app.modules.ingestion.parsers.normalize import normalize
from app.modules.ingestion.parsers.pdf import PageParse

DEFAULT_PAGE_WIDTH = 595.0
DEFAULT_PAGE_HEIGHT = 842.0


def text_block(
    text: str,
    *,
    order: int,
    level: int = 0,
    size: float = 12.0,
    bold: bool = False,
    page_width: float = DEFAULT_PAGE_WIDTH,
    page_height: float = DEFAULT_PAGE_HEIGHT,
    block_type: str = "paragraph",
) -> dict[str, Any]:
    plain = normalize(text)
    return {
        "type": block_type,
        "level": level,
        "text": plain,
        "bbox": [72.0, 72.0, page_width - 72.0, page_height - 72.0],
        "order": order,
        "size": size,
        "bold": bold,
    }


def page_from_blocks(
    page_no: int,
    blocks: list[dict[str, Any]],
    *,
    width: float = DEFAULT_PAGE_WIDTH,
    height: float = DEFAULT_PAGE_HEIGHT,
    source: str = "text",
) -> PageParse:
    plain = "".join(str(b.get("text", "")) for b in blocks)
    return PageParse(
        page_no=page_no,
        width=width,
        height=height,
        blocks=blocks,
        plain_text=plain,
        source=source,
        needs_ocr=False,
    )


def page_from_text(page_no: int, text: str) -> PageParse:
    plain = normalize(text)
    blocks = [text_block(plain, order=0)] if plain.strip() else []
    return page_from_blocks(page_no, blocks)
