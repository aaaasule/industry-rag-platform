"""jieba userdict：parse_rules.dictionary 保持工业复合词整词。"""

from __future__ import annotations

from app.modules.ingestion.chunkers.tsv import build_tsv


def test_dictionary_keeps_compound_token() -> None:
    word = "液压缸座总成"
    tokens = build_tsv(word, dictionary=[word]).split()
    assert word in tokens
