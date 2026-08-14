"""DOCX 解析（python-docx）：样式映射标题；表格转 Markdown。"""

from __future__ import annotations

import io
from typing import Any

from app.modules.ingestion.parsers.common import page_from_blocks, text_block
from app.modules.ingestion.parsers.pdf import PageParse


def parse_docx_bytes(data: bytes) -> list[PageParse]:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = Document(io.BytesIO(data))
    blocks: list[dict[str, Any]] = []
    order = 0

    for block in _iter_block_items(document):
        if isinstance(block, Paragraph):
            text = (block.text or "").strip()
            if not text:
                continue
            level, size, bold = _style_heading(block.style.name if block.style else "")
            blocks.append(text_block(text, order=order, level=level, size=size, bold=bold))
            order += 1
        elif isinstance(block, Table):
            md = _table_to_markdown(block)
            if md.strip():
                blocks.append(text_block(md, order=order, level=0, size=11.0, block_type="table"))
                order += 1

    if not blocks:
        return [page_from_blocks(1, [])]
    # Word 无物理页：整篇作为 1 页，便于分块器按标题切
    return [page_from_blocks(1, blocks)]


def _style_heading(style_name: str) -> tuple[int, float, bool]:
    name = (style_name or "").lower()
    for n in range(1, 7):
        if f"heading {n}" in name or name == f"标题 {n}":
            return n, float(18 - n), True
    if "title" in name or name == "标题":
        return 1, 18.0, True
    return 0, 12.0, False


def _table_to_markdown(table: Any) -> str:
    rows: list[list[str]] = []
    for row in table.rows:
        cells = [" ".join(c.text.split()) for c in row.cells]
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    norm = [r + [""] * (width - len(r)) for r in rows]
    header = norm[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for r in norm[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def _iter_block_items(parent: Any) -> Any:
    """按文档顺序产出 Paragraph / Table。"""
    from docx.document import Document as DocxDocument
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    parent_elm = parent.element.body if isinstance(parent, DocxDocument) else parent._element

    for child in parent_elm.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)
