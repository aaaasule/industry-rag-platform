"""字符规范化：CJK 映射、NFKC、剔除 NUL。"""

from app.modules.ingestion.parsers.normalize import normalize


def test_normalize_strips_nul() -> None:
    assert "\x00" not in normalize("液压\x00泵")
    assert normalize("液压\x00泵") == "液压泵"


def test_normalize_nfkc_and_passthrough() -> None:
    assert normalize("ＨＹＤ－２２０１") == "HYD-2201"
