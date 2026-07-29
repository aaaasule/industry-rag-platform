"""页眉页脚剔除：按 y 聚类取首尾行做频次统计。"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

LINE_TOLERANCE_PT = 6.0
EDGE_LINES = 2
FREQUENCY_RATIO = 0.6
_VARIABLE = re.compile(r"[0-9０-９]+|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|[ivxIVX]{1,6}\b")


def strip_headers_footers(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """pages: [{page_no, width, height, blocks: [{text,bbox,...}]}]"""
    if len(pages) < 3:
        return pages

    header_keys = _repeated(pages, top=True)
    footer_keys = _repeated(pages, top=False)
    drop = header_keys | footer_keys
    if not drop:
        return pages

    cleaned: list[dict[str, Any]] = []
    for page in pages:
        blocks = [b for b in page["blocks"] if _normalize(b.get("text", "")) not in drop]
        cleaned.append({**page, "blocks": blocks, "plain_text": "".join(b["text"] for b in blocks)})
    return cleaned


def _repeated(pages: list[dict[str, Any]], *, top: bool) -> set[str]:
    counter: Counter[str] = Counter()
    for page in pages:
        for text in _edge_lines(page, top=top):
            key = _normalize(text)
            if key:
                counter[key] += 1
    threshold = len(pages) * FREQUENCY_RATIO
    return {k for k, n in counter.items() if n >= threshold}


def _edge_lines(page: dict[str, Any], *, top: bool) -> list[str]:
    lines = _cluster_lines(page.get("blocks", []))
    edge = lines[:EDGE_LINES] if top else lines[-EDGE_LINES:]
    return [t for t in edge if t]


def _cluster_lines(blocks: list[dict[str, Any]]) -> list[str]:
    rows: list[tuple[float, list[str]]] = []
    for block in sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0])):
        y0 = block["bbox"][1]
        if rows and y0 - rows[-1][0] <= LINE_TOLERANCE_PT:
            rows[-1][1].append(block.get("text", ""))
        else:
            rows.append((y0, [block.get("text", "")]))
    return ["".join(parts).strip() for _, parts in rows]


def _normalize(text: str) -> str:
    return _VARIABLE.sub("#", text.strip())
