"""扫描页 OCR，产出与文本层完全一致的 PageSnapshot。

这是本 spike 里最关键的一处设计：OCR 页和文本层页产出同一种中间表示，因此
坐标、编码、标题、页眉页脚这些探针**一行都不用改**就能跑在 OCR 结果上。产品
侧的解析器矩阵也应当遵守同样的约定。

引擎用 RapidOCR（ONNX Runtime 版 PP-OCRv4），与设计文档里写的 PaddleOCR 是
同一套模型，但不需要装 paddlepaddle，在 macOS ARM 上开箱即用。验证坐标质量
这个目的上两者等价。
"""

from __future__ import annotations

import time

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore[no-redef]

from probes.base import PageSnapshot, Span

# OCR 在 200 dpi 上精度与耗时较平衡；再高收益递减，耗时线性上升
DEFAULT_DPI = 200


class OcrEngine:
    """惰性加载的 OCR 引擎。模型初始化有秒级开销，因此整批文档只建一次。"""

    def __init__(self, dpi: int = DEFAULT_DPI) -> None:
        self.dpi = dpi
        self._engine = None

    def _ensure(self):
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR

            self._engine = RapidOCR()
        return self._engine

    def run_page(self, page) -> PageSnapshot:
        engine = self._ensure()
        started = time.perf_counter()

        pixmap = page.get_pixmap(dpi=self.dpi)
        result, _ = engine(pixmap.tobytes("png"))
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        scale = 72.0 / self.dpi  # 像素坐标 → PDF 用户空间（pt）
        spans = [_to_span(item, scale) for item in (result or [])]

        return PageSnapshot(
            page_no=page.number + 1,
            width=page.rect.width,
            height=page.rect.height,
            char_count=sum(len(s.text.strip()) for s in spans),
            image_area_ratio=1.0,
            spans=spans,
            source="ocr",
            ocr_ms=elapsed_ms,
        )


def _to_span(item, scale: float) -> Span:
    """RapidOCR 返回 [四点多边形, 文本, 置信度]，转成轴对齐 bbox。"""
    polygon, text, confidence = item[0], item[1], float(item[2])
    xs = [p[0] * scale for p in polygon]
    ys = [p[1] * scale for p in polygon]
    height_pt = max(ys) - min(ys)

    return Span(
        text=text,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        size=round(height_pt, 1),  # OCR 没有字号，用行高近似，供标题探针打分
        bold=False,                # OCR 不提供字重信息
        confidence=confidence,
    )
