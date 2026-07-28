"""页眉页脚检测。

原本这里复现的是"顶部/底部 8% 区域内频次超 60%"的固定带宽算法，跑真实国标
PDF 时它一条页眉都没抓到。实测数据：页眉底边在页高 10.4% 处，而正文首行顶边
在 11.0% 处——8% 够不着页眉，放宽到 12% 又会吃进正文，可用窗口只有 0.6%。

结论是固定几何带宽这个方法本身不成立，换成**按 y 聚类成行后取每页首尾若干
行**做频次统计。它不依赖任何比例常数，对不同排版自适应。04 文档 2.3 已按此
结论回改。
"""

from __future__ import annotations

import re
from collections import Counter

from probes.base import DocSnapshot, Finding, PageSnapshot

LINE_TOLERANCE_PT = 6.0
EDGE_LINES = 2  # 每页首尾各考察几行
FREQUENCY_RATIO = 0.6
MIN_PAGES = 3

# 页码每页都不同，归一化后才能被频次统计捕捉到；国标文档前言部分用罗马数字
_VARIABLE = re.compile(r"[0-9０-９]+|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|[ivxIVX]{1,6}\b")


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

        headers = _repeated(doc, top=True)
        footers = _repeated(doc, top=False)
        risky = [text for text, _ in headers + footers if len(text) > 30]

        return [
            Finding(
                metric="识别到的页眉",
                value=len(headers),
                level="ok" if headers else "warn",
                note=_render(headers) or "未识别到固定页眉，请对照原文确认是否确实没有",
            ),
            Finding(
                metric="识别到的页脚",
                value=len(footers),
                level="ok" if footers else "warn",
                note=_render(footers) or "未识别到固定页脚",
                impact="页码需保留用于溯源但不能进入 chunk 文本，见 04 文档 2.3",
            ),
            Finding(
                metric="误伤风险",
                value="高" if risky else "低",
                level="warn" if risky else "ok",
                note=_render([(t, 0) for t in risky]) or "被判定的行都很短，不像正文",
                impact="误伤时正文会被整行剔除，且不会有任何报错，属于静默的信息丢失",
            ),
        ]


def _repeated(doc: DocSnapshot, top: bool) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for page in doc.pages:
        for text in _edge_lines(page, top):
            counter[_normalize(text)] += 1

    threshold = len(doc.pages) * FREQUENCY_RATIO
    return [(text, n) for text, n in counter.most_common() if n >= threshold and text]


def _edge_lines(page: PageSnapshot, top: bool) -> list[str]:
    lines = _cluster_lines(page)
    edge = lines[:EDGE_LINES] if top else lines[-EDGE_LINES:]
    return [text for text in edge if text]


def _cluster_lines(page: PageSnapshot) -> list[str]:
    """按 y 坐标把 span 聚成行，返回自上而下的行文本。"""
    rows: list[tuple[float, list[str]]] = []
    for span in sorted(page.spans, key=lambda s: (s.bbox[1], s.bbox[0])):
        if rows and span.bbox[1] - rows[-1][0] <= LINE_TOLERANCE_PT:
            rows[-1][1].append(span.text)
        else:
            rows.append((span.bbox[1], [span.text]))
    return ["".join(parts).strip() for _, parts in rows]


def _normalize(text: str) -> str:
    return _VARIABLE.sub("#", text.strip())


def _render(lines: list[tuple[str, int]], limit: int = 4) -> str:
    return " ｜ ".join(
        f"“{text}”×{n}" if n else f"“{text[:24]}…”" for text, n in lines[:limit]
    )
