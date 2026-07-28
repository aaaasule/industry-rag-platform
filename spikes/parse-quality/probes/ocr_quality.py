"""OCR 输出质量：只在存在 OCR 页时生效。

坐标、编码、标题这些探针已经会自动跑在 OCR 结果上（OCR 产出同一种中间表示），
这里只补充 OCR 特有的两件事：识别置信度，以及每页耗时——后者直接决定 M1 的
摄取工期与 worker-parse 规格能不能按原计划定。
"""

from __future__ import annotations

from statistics import median

from probes.base import DocSnapshot, Finding, grade

LOW_CONFIDENCE = 0.80


class OcrQualityProbe:
    name = "OCR 质量"

    def run(self, doc: DocSnapshot) -> list[Finding]:
        ocr_pages = [p for p in doc.pages if p.source == "ocr"]
        if not ocr_pages:
            return []

        spans = [s for p in ocr_pages for s in p.spans if s.confidence is not None]
        if not spans:
            return [
                Finding(
                    metric="OCR 识别结果",
                    value="空",
                    level="fail",
                    note=f"{len(ocr_pages)} 页执行了 OCR 但一个文本框都没识别出来",
                    impact="该类文档无法入库，需检查图像质量或更换 OCR 引擎",
                )
            ]

        confidences = [s.confidence for s in spans]
        low = [c for c in confidences if c < LOW_CONFIDENCE]
        per_page_ms = [p.ocr_ms for p in ocr_pages]
        chars = sum(p.char_count for p in ocr_pages)

        return [
            Finding(
                metric="OCR 页数与产出",
                value=f"{len(ocr_pages)} 页 / {len(spans)} 文本框 / {chars} 字",
                level="ok",
                note=f"平均每页 {chars // len(ocr_pages)} 字",
            ),
            Finding(
                metric="平均置信度",
                value=f"{sum(confidences) / len(confidences):.3f}",
                level=grade(
                    len(low) / len(confidences), warn_at=0.05, fail_at=0.15
                ),
                note=f"低于 {LOW_CONFIDENCE} 的占 {len(low) / len(confidences):.1%}",
                impact="低置信度文本进入索引会污染检索，需在解析阶段按阈值丢弃或标记",
            ),
            Finding(
                metric="单页 OCR 耗时",
                value=f"中位 {median(per_page_ms):.0f} ms / 最大 {max(per_page_ms)} ms",
                level=grade(median(per_page_ms), warn_at=3000, fail_at=8000),
                note=f"按此速度，100 页扫描件约需 {median(per_page_ms) * 100 / 1000:.0f} 秒",
                impact="超过 05 文档给出的「100 页 OCR < 5 min」目标时，需增加 worker-parse 副本或降低 DPI",
            ),
        ]
