"""Markdown / 纯文本解析。"""

from __future__ import annotations

import re

from app.modules.ingestion.parsers.common import page_from_blocks, text_block
from app.modules.ingestion.parsers.normalize import normalize
from app.modules.ingestion.parsers.pdf import PageParse

_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")


def parse_text_bytes(data: bytes, *, mime_type: str = "text/plain") -> list[PageParse]:
    text = normalize(data.decode("utf-8", errors="ignore"))
    if not text.strip():
        return [page_from_blocks(1, [])]

    is_md = "markdown" in mime_type.lower() or bool(_HEADING.match(text.lstrip().split("\n", 1)[0]))
    if not is_md:
        # 纯文本按空行切段，避免整文件一块导致 embedding 超长 400
        blocks = []
        order = 0
        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if not para:
                continue
            blocks.append(text_block(para, order=order))
            order += 1
        return [page_from_blocks(1, blocks or [text_block(text, order=0)])]

    blocks = []
    order = 0
    for line in text.splitlines():
        m = _HEADING.match(line.strip())
        if m:
            level = len(m.group(1))
            blocks.append(
                text_block(
                    m.group(2).strip(),
                    order=order,
                    level=level,
                    size=float(18 - level),
                    bold=True,
                )
            )
            order += 1
            continue
        if line.strip():
            blocks.append(text_block(line, order=order))
            order += 1
    return [page_from_blocks(1, blocks or [text_block(text, order=0)])]
