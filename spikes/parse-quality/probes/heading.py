"""标题层级识别：结构感知分块的前提。

04 文档 3.1 的分块算法第一步就是"按标题层级切成语义段"。如果标题识别不出
来，整个算法退化成按长度硬切，heading_path 前缀也无从谈起。这里直接复现
2.3 节的打分规则跑一遍真实文档，看识别率够不够。
"""

from __future__ import annotations

import re
from collections import Counter

from probes.base import DocSnapshot, Finding, PageSnapshot, Span

# 编号后允许直接跟中文：国标文档普遍写成「1范围」「4.1企业应制定…」而非「1 范围」。
# 原规则要求编号后必须有分隔符，在真实 AQ 标准上一条都匹配不到。
NUMBERING = re.compile(r"^\d+(\.\d+)*(?:[\s、.．]|(?=[\u4e00-\u9fff])|$)")
CLAUSE_INLINE = re.compile(r"^\d+(\.\d+)+(?=[\u4e00-\u9fff])")
SCORE_THRESHOLD = 3
MAX_HEADING_CHARS = 40


class HeadingProbe:
    name = "标题层级"

    def run(self, doc: DocSnapshot) -> list[Finding]:
        body_size = _body_font_size(doc)
        headings = [
            (page.page_no, span)
            for page in doc.pages
            for span in page.spans
            if _score(span, body_size) >= SCORE_THRESHOLD
        ]

        findings = [
            Finding(
                metric="PDF 大纲",
                value=f"{len(doc.outline)} 项" if doc.has_outline else "无",
                level="ok" if doc.has_outline else "warn",
                note="有大纲时直接采用，识别质量最可靠",
                impact="无大纲则完全依赖启发式打分，需人工确认下方识别结果是否合理",
            ),
            Finding(
                metric="正文字号",
                value=body_size,
                level="ok",
                note="按字符数加权取众数，作为标题判定的基准",
            ),
            Finding(
                metric="启发式识别标题数",
                value=len(headings),
                level=_heading_level(doc, headings),
                note=_sample(headings),
                impact="识别为 0 时结构感知分块退化为长度切分，需回改 04 文档 3.1",
            ),
        ]

        clauses = [
            span
            for page in doc.pages
            for span in page.spans
            if CLAUSE_INLINE.match(span.text.strip())
        ]
        if clauses:
            findings.append(
                Finding(
                    metric="条款式内联编号",
                    value=f"{len(clauses)} 行",
                    level="warn",
                    note=f"样例：{clauses[0].text.strip()[:38]}…",
                    impact=(
                        "标准类文档的结构单位是行首条款号而非独立标题行，"
                        "分块需按条款边界切分，仅靠标题层级会把整章并成一块"
                    ),
                )
            )

        numbered = sum(1 for _, span in headings if NUMBERING.match(span.text.strip()))
        if headings:
            findings.append(
                Finding(
                    metric="带编号标题占比",
                    value=f"{numbered / len(headings):.0%}",
                    level="ok",
                    note="工业文档编号规整时，编号模式比字号更可靠，权重应更高",
                )
            )
        return findings


def _body_font_size(doc: DocSnapshot) -> float:
    counter: Counter[float] = Counter()
    for page in doc.pages:
        for span in page.spans:
            counter[span.size] += len(span.text.strip())
    return counter.most_common(1)[0][0] if counter else 0.0


def _score(span: Span, body_size: float) -> int:
    text = span.text.strip()
    if not text or len(text) > MAX_HEADING_CHARS:
        return 0
    score = 0
    if NUMBERING.match(text):
        score += 3  # 编号模式权重最高，工业文档章节编号非常规整
    if body_size and span.size > body_size * 1.15:
        score += 2
    if span.bold:
        score += 1
    return score


def _heading_level(doc: DocSnapshot, headings: list[tuple[int, Span]]):
    if headings:
        return "ok"
    return "warn" if doc.has_outline else "fail"


def _sample(headings: list[tuple[int, Span]], limit: int = 5) -> str:
    if not headings:
        return "未识别到任何标题，请人工确认该文档是否确实无章节结构"
    shown = " ｜ ".join(f"p{no} {span.text.strip()}" for no, span in headings[:limit])
    return f"样例：{shown}"
