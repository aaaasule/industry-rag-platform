"""Reciprocal Rank Fusion — 多路召回排名融合。"""

from __future__ import annotations


def rrf_fuse(ranked_lists: list[list[str]], *, k: int = 60) -> list[tuple[str, float]]:
    """将多路有序 id 列表融合为 (id, score) 列表，按 score 降序。

    每路列表内 rank 从 0 计，贡献 ``1 / (k + rank + 1)``。
    """
    scores: dict[str, float] = {}
    for ranks in ranked_lists:
        for pos, item_id in enumerate(ranks):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + pos + 1)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))
