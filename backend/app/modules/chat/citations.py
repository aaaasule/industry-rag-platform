"""生成后引用编号校验与清洗。"""

from __future__ import annotations

import re

_CITATION_RE = re.compile(r"\[(\d+)\]")


def validate_citations(text: str, max_index: int) -> tuple[str, list[int]]:
    """校验正文中的 ``[n]`` 引用标记，剔除越界编号。

    返回清洗后的正文，以及按出现顺序去重后的 1-based 有效引用编号列表。
    """
    used: list[int] = []
    seen: set[int] = set()

    def _replace(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if 1 <= index <= max_index:
            if index not in seen:
                used.append(index)
                seen.add(index)
            return match.group(0)
        return ""

    cleaned = _CITATION_RE.sub(_replace, text)
    return cleaned, used
