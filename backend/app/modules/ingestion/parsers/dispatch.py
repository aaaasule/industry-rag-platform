"""按 mime / 魔数分派解析器。"""

from __future__ import annotations

from collections.abc import Callable

from app.modules.ingestion.parsers.docx_parser import parse_docx_bytes
from app.modules.ingestion.parsers.pdf import PageParse, parse_pdf_bytes
from app.modules.ingestion.parsers.pptx_parser import parse_pptx_bytes
from app.modules.ingestion.parsers.text_parser import parse_text_bytes
from app.modules.ingestion.parsers.xlsx_parser import parse_xlsx_bytes

ProgressCallback = Callable[[int, int], None]


def detect_format(data: bytes, mime_type: str) -> str:
    mime = (mime_type or "").lower()
    if data[:5].startswith(b"%PDF") or "pdf" in mime:
        return "pdf"
    if data[:2] == b"PK":
        # OOXML zip：靠 mime / 后续失败回退
        if "wordprocessingml" in mime or mime.endswith("msword") or "docx" in mime:
            return "docx"
        if "spreadsheetml" in mime or "excel" in mime or "xlsx" in mime:
            return "xlsx"
        if "presentationml" in mime or "powerpoint" in mime or "pptx" in mime:
            return "pptx"
        # 无明确 mime 时试 docx（最常见）
        if "officedocument" in mime:
            if "sheet" in mime:
                return "xlsx"
            if "presentation" in mime:
                return "pptx"
            return "docx"
    if "markdown" in mime or mime in {"text/x-markdown", "text/markdown"}:
        return "markdown"
    if mime.startswith("text/") or mime in {"application/json", "application/xml"}:
        return "text"
    # 兜底：尝试 utf-8 文本
    try:
        data.decode("utf-8")
        return "text"
    except UnicodeDecodeError:
        return "unknown"


def parse_document_bytes(
    data: bytes,
    mime_type: str,
    *,
    ocr_workers: int = 4,
    on_ocr_progress: ProgressCallback | None = None,
) -> list[PageParse]:
    kind = detect_format(data, mime_type)
    if kind == "pdf":
        return _parse_pdf(data, ocr_workers=ocr_workers, on_ocr_progress=on_ocr_progress)
    if kind == "docx":
        return parse_docx_bytes(data)
    if kind == "xlsx":
        return parse_xlsx_bytes(data)
    if kind == "pptx":
        return parse_pptx_bytes(data)
    if kind in {"markdown", "text"}:
        return parse_text_bytes(data, mime_type=mime_type if kind == "markdown" else "text/plain")
    raise ValueError(f"unsupported_document_format: mime={mime_type!r}")


def _parse_pdf(
    data: bytes,
    *,
    ocr_workers: int,
    on_ocr_progress: ProgressCallback | None,
) -> list[PageParse]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    pages = parse_pdf_bytes(data)
    ocr_idxs = [i for i, p in enumerate(pages) if p.needs_ocr]
    if not ocr_idxs:
        if on_ocr_progress:
            on_ocr_progress(0, 0)
        return pages

    workers = max(1, min(ocr_workers, len(ocr_idxs)))
    total = len(ocr_idxs)
    done = 0

    def _ocr_page_no(page_no: int) -> PageParse:
        try:
            import pymupdf as fitz
        except ImportError:  # pragma: no cover
            import fitz  # type: ignore[no-redef]
        from app.modules.ingestion.parsers.ocr import ocr_page

        doc = fitz.open(stream=data, filetype="pdf")
        try:
            return ocr_page(doc[page_no - 1])
        finally:
            doc.close()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_ocr_page_no, pages[i].page_no): i for i in ocr_idxs}
        for fut in as_completed(futures):
            idx = futures[fut]
            pages[idx] = fut.result()
            done += 1
            if on_ocr_progress:
                on_ocr_progress(done, total)

    return pages


def guess_mime_from_filename(filename: str) -> str | None:
    lower = filename.lower()
    mapping: dict[str, str] = {
        ".pdf": "application/pdf",
        ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".txt": "text/plain",
    }
    for ext, mime in mapping.items():
        if lower.endswith(ext):
            return mime
    return None


def supported_upload_extensions() -> tuple[str, ...]:
    return (".pdf", ".docx", ".xlsx", ".pptx", ".md", ".markdown", ".txt")
