"""OCR 回退（可选依赖 rapidocr-onnxruntime）。"""

from __future__ import annotations

from typing import Any

from app.modules.ingestion.parsers.normalize import normalize
from app.modules.ingestion.parsers.pdf import PageParse

DEFAULT_DPI = 200


def ocr_page(page: Any, *, dpi: int = DEFAULT_DPI) -> PageParse:
    """对 PyMuPDF page 做 OCR，产出与文本层同结构的 PageParse。

    缺依赖时抛 RuntimeError，由上层标记 failed/retryable。
    """
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "未安装 OCR 依赖。本地请执行：cd backend && uv sync --extra ocr"
        ) from exc

    engine = RapidOCR()
    pixmap = page.get_pixmap(dpi=dpi)
    result, _ = engine(pixmap.tobytes("png"))
    scale = 72.0 / dpi
    blocks: list[dict[str, Any]] = []
    for i, item in enumerate(result or []):
        polygon, text, confidence = item[0], item[1], float(item[2])
        xs = [p[0] * scale for p in polygon]
        ys = [p[1] * scale for p in polygon]
        height_pt = max(ys) - min(ys)
        blocks.append(
            {
                "type": "paragraph",
                "level": 0,
                "text": normalize(text),
                "bbox": [min(xs), min(ys), max(xs), max(ys)],
                "order": i,
                "size": round(height_pt, 1),
                "bold": False,
                "ocr_confidence": confidence,
            }
        )
    plain = "".join(b["text"] for b in blocks)
    return PageParse(
        page_no=page.number + 1,
        width=float(page.rect.width),
        height=float(page.rect.height),
        blocks=blocks,
        plain_text=plain,
        source="ocr",
        needs_ocr=False,
    )
