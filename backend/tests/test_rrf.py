"""RRF 融合单元测试。"""

from __future__ import annotations

from app.modules.retrieval.rrf import rrf_fuse


def test_rrf_fuse_merges_two_ranked_lists() -> None:
    vector = ["chunk-a", "chunk-b", "chunk-c"]
    fulltext = ["chunk-b", "chunk-c", "chunk-a"]

    fused = rrf_fuse([vector, fulltext], k=60)

    assert [item_id for item_id, _ in fused] == ["chunk-b", "chunk-a", "chunk-c"]

    scores = dict(fused)
    assert scores["chunk-b"] == 1 / 61 + 1 / 62
    assert scores["chunk-a"] == 1 / 61 + 1 / 63
    assert scores["chunk-c"] == 1 / 62 + 1 / 63


def test_rrf_fuse_empty_lists() -> None:
    assert rrf_fuse([]) == []


def test_rrf_fuse_custom_k() -> None:
    fused = rrf_fuse([["only"]], k=10)
    assert fused == [("only", 1 / 11)]
