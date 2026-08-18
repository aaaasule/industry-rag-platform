"""查询侧术语同义词：最长别名优先、单次扫描替换。"""

from __future__ import annotations

import re
from typing import Any


def coerce_synonyms(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        src, dst = key.strip(), value.strip()
        if src and dst and src != dst:
            out[src] = dst
    return out


def apply_synonyms(text: str, synonyms: dict[str, str] | None) -> str:
    if not text or not synonyms:
        return text
    aliases = [src for src in synonyms if src]
    if not aliases:
        return text
    aliases.sort(key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(src) for src in aliases))
    return pattern.sub(lambda m: synonyms[m.group(0)], text)
