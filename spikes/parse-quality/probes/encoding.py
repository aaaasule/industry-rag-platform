"""字符编码规范性：提取出的文本是不是"能检索的文本"。

这项检查是跑真实国标 PDF 时补上的。大量 GB/AQ 系列标准使用了带错误
ToUnicode CMap 的字体，拉丁字母会被映射到 CJK 汉字区——`AQ/T 4127—2018`
提取出来是 `犃犙／犜４１２７—２０１８`。中文正常，字母和数字全废。

这直接击穿 04 文档 5.2 的核心论点：混合检索里 BM25 存在的意义就是精确命中
型号、标准号、错误码。如果这些字符串在入库时就不是 ASCII，BM25 这一路等于
没有。
"""

from __future__ import annotations

import unicodedata

from probes.base import DocSnapshot, Finding, grade

# 国标 PDF 常见的错误映射表：CJK 汉字 → 拉丁字母
_UPPER = "犃犅犆犇犈犉犌犎犐犑犓犔犕犖犗犘犙犚犛犜犝犞犠犡犢犣"
_LOWER = "犪犫犮犱犲犳犵犺犻犼犽犾犿狀狅狆狇狉狊狋狌狏狑狓狔狕"

CJK_LATIN_MAP: dict[int, str] = {
    ord(c): chr(ord("A") + i) for i, c in enumerate(_UPPER)
}
CJK_LATIN_MAP.update({ord(c): chr(ord("a") + i) for i, c in enumerate(_LOWER)})


def repair(text: str) -> str:
    """还原错误映射并把全角转半角。产品侧应在解析后、分块前执行同样的操作。"""
    return unicodedata.normalize("NFKC", text.translate(CJK_LATIN_MAP))


class EncodingProbe:
    name = "字符编码"

    def run(self, doc: DocSnapshot) -> list[Finding]:
        raw = "".join(span.text for page in doc.pages for span in page.spans)
        if not raw:
            return [
                Finding(
                    metric="字符编码",
                    value="无文本",
                    level="skip",
                    note="纯扫描件，编码问题需在 OCR 输出上重新评估",
                )
            ]

        mismapped = [c for c in raw if ord(c) in CJK_LATIN_MAP]
        fullwidth = [c for c in raw if c != unicodedata.normalize("NFKC", c)]

        return [
            Finding(
                metric="字母错误映射",
                value=f"{len(mismapped)} 处（{len(set(mismapped))} 种）",
                level="fail" if mismapped else "ok",
                note=_preview(raw, mismapped),
                impact="标准号/型号在入库时不是 ASCII，BM25 精确匹配完全失效，需在解析后加字符还原步骤",
            ),
            Finding(
                metric="全角字符占比",
                value=f"{len(fullwidth) / len(raw):.1%}",
                level=grade(len(fullwidth) / len(raw), warn_at=0.01, fail_at=0.05),
                note="全角数字与标点需 NFKC 归一化，否则 “４１２７” 与用户输入的 “4127” 无法匹配",
                impact="影响 BM25 命中率与 jieba 分词质量",
            ),
        ]


def _preview(raw: str, mismapped: list[str]) -> str:
    if not mismapped:
        return "未检出错误映射"
    idx = raw.index(mismapped[0])
    sample = raw[max(0, idx - 4) : idx + 24]
    return f"样例：{sample!r} → {repair(sample)!r}"
