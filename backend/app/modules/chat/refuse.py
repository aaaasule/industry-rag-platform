"""拒答判定。"""

from __future__ import annotations

from app.modules.retrieval.base import SearchHit

DEFAULT_MIN_SCORE = 0.35


def should_refuse(hits: list[SearchHit], *, min_score: float = DEFAULT_MIN_SCORE) -> str | None:
    """返回拒答原因码；不应拒答时返回 None。

    分数阈值对照向量相似度（0~1）。RRF 分数量纲不同，不单独用 0.35 卡。
    """
    if not hits:
        return "no_relevant_evidence"
    top_vec = hits[0].scores.get("vector")
    if top_vec is not None and float(top_vec) < min_score:
        return "low_score"
    return None
