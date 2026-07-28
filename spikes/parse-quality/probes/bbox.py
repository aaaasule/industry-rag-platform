"""坐标可用性：ADR-005 成立与否的前提。

设计里"引用溯源精确到坐标"贯穿解析、chunks.bboxes 存储、引用接口和前端
pdf.js 高亮层四个环节。如果真实文档里拿不到可靠坐标，要改的不是一处代码，
而是四份文档。因此这项检查的 fail 阈值定得很低。
"""

from __future__ import annotations

import math

from probes.base import DocSnapshot, Finding, Span, grade

# 允许少量越界：部分排版会让字形轻微超出裁剪框
TOLERANCE_PT = 2.0


class BBoxProbe:
    name = "坐标"

    def run(self, doc: DocSnapshot) -> list[Finding]:
        total = 0
        malformed: list[str] = []
        out_of_page: list[str] = []

        for page in doc.pages:
            for span in page.spans:
                total += 1
                if not _is_wellformed(span):
                    malformed.append(f"p{page.page_no}")
                elif not _is_inside(span, page.width, page.height):
                    out_of_page.append(f"p{page.page_no}")

        if total == 0:
            return [
                Finding(
                    metric="坐标可用性",
                    value="无文本 span",
                    level="skip",
                    note="该文档没有文本层，坐标需在 OCR 后另行验证",
                )
            ]

        bad_ratio = len(malformed) / total
        out_ratio = len(out_of_page) / total

        return [
            Finding(
                metric="非法坐标占比",
                value=f"{bad_ratio:.2%}（{len(malformed)}/{total}）",
                level=grade(bad_ratio, warn_at=0.005, fail_at=0.02),
                note="非法指 NaN、零面积或左右上下颠倒",
                impact="超标则 chunks.bboxes 与前端高亮层需要重新设计，ADR-005 面临推翻",
            ),
            Finding(
                metric="越界坐标占比",
                value=f"{out_ratio:.2%}（{len(set(out_of_page))} 页涉及）",
                level=grade(out_ratio, warn_at=0.01, fail_at=0.05),
                note=f"超出页面边界 {TOLERANCE_PT} pt 以上",
                impact="通常意味着页面存在旋转或裁剪框偏移，高亮位置会整体错位",
            ),
            Finding(
                metric="页面尺寸一致性",
                value=_size_summary(doc),
                level="ok" if _size_consistent(doc) else "warn",
                note="尺寸不一致时前端必须逐页按 document_pages.width/height 换算，不能全局缩放",
            ),
        ]


def _is_wellformed(span: Span) -> bool:
    x0, y0, x1, y1 = span.bbox
    if any(math.isnan(v) or math.isinf(v) for v in span.bbox):
        return False
    return x1 > x0 and y1 > y0


def _is_inside(span: Span, width: float, height: float) -> bool:
    x0, y0, x1, y1 = span.bbox
    return (
        x0 >= -TOLERANCE_PT
        and y0 >= -TOLERANCE_PT
        and x1 <= width + TOLERANCE_PT
        and y1 <= height + TOLERANCE_PT
    )


def _sizes(doc: DocSnapshot) -> set[tuple[int, int]]:
    return {(round(p.width), round(p.height)) for p in doc.pages}


def _size_consistent(doc: DocSnapshot) -> bool:
    return len(_sizes(doc)) <= 1


def _size_summary(doc: DocSnapshot) -> str:
    sizes = sorted(_sizes(doc))
    shown = ", ".join(f"{w}×{h}" for w, h in sizes[:3])
    return shown if len(sizes) <= 3 else f"{shown} … 共 {len(sizes)} 种"
