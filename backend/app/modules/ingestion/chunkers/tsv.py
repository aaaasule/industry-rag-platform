"""中文全文检索分词。"""

from __future__ import annotations


def build_tsv(text: str) -> str:
    try:
        import jieba
    except ImportError:  # pragma: no cover
        return text
    tokens = jieba.lcut_for_search(text)
    return " ".join(t for t in tokens if t.strip())
