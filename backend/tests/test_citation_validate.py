"""引用编号校验单元测试。"""

from __future__ import annotations

from app.modules.chat.citations import validate_citations


def test_validate_citations_removes_out_of_range_index() -> None:
    text = "压力上限为 16 MPa[1][99]。"
    cleaned, used = validate_citations(text, max_index=5)

    assert cleaned == "压力上限为 16 MPa[1]。"
    assert used == [1]


def test_validate_citations_keeps_valid_indexes_in_order() -> None:
    text = "见[3]与[1]说明。"
    cleaned, used = validate_citations(text, max_index=8)

    assert cleaned == text
    assert used == [3, 1]


def test_validate_citations_deduplicates_used_indexes() -> None:
    text = "重复引用[2][2][4]。"
    cleaned, used = validate_citations(text, max_index=5)

    assert cleaned == text
    assert used == [2, 4]


def test_validate_citations_removes_zero_index() -> None:
    text = "无效[0]有效[1]。"
    cleaned, used = validate_citations(text, max_index=3)

    assert cleaned == "无效有效[1]。"
    assert used == [1]


def test_validate_citations_no_markers() -> None:
    text = "没有任何引用标记。"
    cleaned, used = validate_citations(text, max_index=5)

    assert cleaned == text
    assert used == []
