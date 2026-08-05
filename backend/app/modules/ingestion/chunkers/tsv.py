"""中文全文检索分词。"""

from __future__ import annotations

from collections.abc import Sequence


def build_tsv(text: str, dictionary: Sequence[str] | None = None) -> str:
    try:
        import jieba
    except ImportError:  # pragma: no cover
        return text
    if dictionary:
        from app.modules.ingestion.chunkers.dictionary import ensure_jieba_userdict

        ensure_jieba_userdict(dictionary)
    tokens = jieba.lcut_for_search(text)
    return " ".join(t for t in tokens if t.strip())
