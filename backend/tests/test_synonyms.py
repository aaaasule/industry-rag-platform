"""查询侧同义词替换。"""

from app.modules.retrieval.synonyms import apply_synonyms, coerce_synonyms


def test_longest_alias_wins() -> None:
    synonyms = {"泵": "泵X", "泵浦": "液压泵"}
    assert apply_synonyms("检查泵浦压力", synonyms) == "检查液压泵压力"
    assert apply_synonyms("泵与泵浦", synonyms) == "泵X与液压泵"


def test_empty_or_identity_noop() -> None:
    assert apply_synonyms("泵", None) == "泵"
    assert coerce_synonyms({"泵": "泵", " ": "x", 1: "a"}) == {}
    assert coerce_synonyms({"泵浦": "泵"}) == {"泵浦": "泵"}
