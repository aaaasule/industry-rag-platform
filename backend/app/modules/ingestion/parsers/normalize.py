"""字符规范化：国标 PDF 错误映射还原 + NFKC。"""

from __future__ import annotations

import unicodedata

_UPPER = "犃犅犆犇犈犉犌犎犐犑犓犔犕犖犗犘犙犚犛犜犝犞犠犡犢犣"
_LOWER = "犪犫犮犱犲犳犵犺犻犼犽犾犿狀狅狆狇狉狊狋狌狏狑狓狔狕"

CJK_LATIN_MAP: dict[int, str] = {ord(c): chr(ord("A") + i) for i, c in enumerate(_UPPER)}
CJK_LATIN_MAP.update({ord(c): chr(ord("a") + i) for i, c in enumerate(_LOWER)})


def normalize(text: str) -> str:
    """索引侧与查询侧必须共用这一份实现。

    去掉 ``\\u0000``：部分 PDF 字体抽取会带上空字符，Postgres text/jsonb 无法存储。
    """
    cleaned = text.replace("\x00", "").translate(CJK_LATIN_MAP)
    return unicodedata.normalize("NFKC", cleaned)
