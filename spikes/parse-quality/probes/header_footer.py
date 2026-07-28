"""页眉页脚检测：直接复现 04 文档 2.3 的剔除算法。

规则是"页面顶部/底部 8% 区域内，出现频次超过页数 60% 的行判为页眉页脚"。
在真实排版上跑一遍，既验证阈值是否合适，也顺便看看有没有把正文误伤。
"""

from __future__ import annotations

import re
from collections import Counter

from probes.base import DocSnapshot, Finding, PageSnapshot

BAND_RATIO = 0.08
FREQUENCY_RATIO = 0.6
MIN_PAGES = 3

# 页码本身每页都不同，归一化后才能被频次统计捕捉到
_DIGITS = re.compile(r"\d+")


class HeaderFooterProbe:
    name = "页眉页脚"

    def run(self, doc: DocSnapshot) -> list[Finding]:
        if len(doc.pages) < MIN_PAGES:
            return [
                Finding(
                    metric="页眉页脚",
                    value="未执行",
                    level="skip",
                    note=f"页数少于 {MIN_PAGES}，频次统计无意义",
                )
            ]

        headers = _repeated_lines(doc, top=True)
        footers = _repeated_lines(doc, top=False)

        return [
            Finding(
                metric="识别到的页眉",
                value=len(headers),
                level="ok",
                note=_render(headers) or "未识别到固定页眉",
            ),
            Finding(
                metric="识别到的页脚",
                value=len(footers),
                level="ok",
                note=_render(footers) or "未识别到固定页脚",
                impact="页码需保留用于溯源但不能进入 chunk 文本，见 04 文档 2.3",
            ),
            Finding(
                metric="误伤风险",
                value=_risk_level(headers + footers),
                level="warn" if _risk_level(headers + footers) != "低" else "ok",
                note="被判定的行若明显是正文（长句、含实质信息），说明阈值需要按该排版调整",
            ),
        ]


def _repeated_lines(doc: DocSnapshot, top: bool) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for page in doc.pages:
        for text in _band_texts(page, top):
            counter[_normalize(text)] += 1

    threshold = len(doc.pages) * FREQUENCY_RATIO
    return [(text, n) for text, n in counter.most_common() if n >= threshold and text]


def _band_texts(page: PageSnapshot, top: bool) -> list[str]:
    band = page.height * BAND_RATIO

    def in_band(span) -> bool:
        if top:
            return span.bbox[3] <= band  # 整个 span 落在顶部带内
        return span.bbox[1] >= page.height - band

    return [span.text.strip() for span in page.spans if in_band(span)]


def _normalize(text: str) -> str:
    return _DIGITS.sub("#", text.strip())


def _risk_level(lines: list[tuple[str, int]]) -> str:
    return "高" if any(len(text) > 30 for text, _ in lines) else "低"


def _render(lines: list[tuple[str, int]], limit: int = 4) -> str:
    shown = " ｜ ".join(f"“{text}”×{n}" for text, n in lines[:limit])
    return shown
