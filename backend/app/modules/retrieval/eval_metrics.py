from __future__ import annotations


def relevant_rank(hits: list[dict], row: dict) -> int | None:
    """返回首个相关命中的 1-based 排名；无关则 None。"""
    ids = {str(x) for x in (row.get("expected_document_ids") or [])}
    titles = [str(t).lower() for t in (row.get("expected_document_titles") or []) if t]
    if not ids and not titles:
        return None
    for i, h in enumerate(hits, start=1):
        doc_id = str(h.get("document_id") or "")
        title = str(h.get("document_title") or "").lower()
        if ids and doc_id in ids:
            return i
        if titles and any(t in title for t in titles):
            return i
    return None
