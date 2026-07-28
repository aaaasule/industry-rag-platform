"""文本层覆盖率：有多少页必须走 OCR。

阈值与 04 文档 2.2 节的 needs_ocr 规则保持一致。提前跑一遍是为了在动手写
摄取代码之前就知道 OCR 的真实成本——它同时决定 M1 的工期和 PaddleOCR 的
部署规格。
"""

from __future__ import annotations

from probes.base import DocSnapshot, Finding, PageSnapshot, grade

CHAR_THRESHOLD = 50
IMAGE_RATIO_THRESHOLD = 0.5


def needs_ocr(page: PageSnapshot) -> bool:
    """判定一页是否需要 OCR。

    已经被 OCR 处理过的页面直接算作"需要"——否则开启 --ocr 后本项指标会因为
    页面已有文本而归零，正好把它要度量的成本给隐藏掉。
    """
    if page.source == "ocr":
        return True
    return page.char_count < CHAR_THRESHOLD and page.image_area_ratio > IMAGE_RATIO_THRESHOLD


class TextLayerProbe:
    name = "文本层"

    def run(self, doc: DocSnapshot) -> list[Finding]:
        total = len(doc.pages) or 1
        ocr_pages = [p.page_no for p in doc.pages if needs_ocr(p)]
        blank_pages = [
            p.page_no
            for p in doc.pages
            if p.char_count == 0 and p.image_area_ratio <= IMAGE_RATIO_THRESHOLD
        ]
        ratio = len(ocr_pages) / total

        findings = [
            Finding(
                metric="需 OCR 页占比",
                value=f"{ratio:.1%}（{len(ocr_pages)}/{total} 页）",
                level=grade(ratio, warn_at=0.05, fail_at=0.30),
                note=_ocr_note(ocr_pages),
                impact="占比高意味着摄取耗时与 OCR 算力成本大幅上升，需重估 M1 工期与 worker-parse 规格",
            ),
            Finding(
                metric="每页平均字符数",
                value=round(sum(p.char_count for p in doc.pages) / total),
                level="ok",
                note="用于判断文本层是否完整；异常偏低往往是嵌入字体未正确解码",
            ),
        ]

        if blank_pages:
            findings.append(
                Finding(
                    metric="疑似解析失败页",
                    value=_preview(blank_pages),
                    level="warn",
                    note="既无文本也无图片，通常是字体编码异常或页面本身为空",
                    impact="若为编码异常，这部分内容会静默缺失，用户会以为资料已完整入库",
                )
            )
        return findings


def _ocr_note(ocr_pages: list[int]) -> str:
    if not ocr_pages:
        return "全部页面存在可用文本层，无需 OCR"
    return f"需 OCR 的页码：{_preview(ocr_pages)}"


def _preview(pages: list[int], limit: int = 12) -> str:
    head = ", ".join(str(p) for p in pages[:limit])
    return head if len(pages) <= limit else f"{head} … 共 {len(pages)} 页"
