"""摄取解析与分块单元测试（不依赖数据库）。"""

from __future__ import annotations

from app.modules.ingestion.chunkers.structure import ChunkRules, chunk_pages
from app.modules.ingestion.parsers.normalize import normalize


def test_normalize_repairs_cjk_latin_and_nfkc() -> None:
    # 犃→A，全角数字 NFKC
    assert normalize("犃Ｑ／Ｔ１２３") == "AQ/T123"
    assert "犃" not in normalize("标准犃犚")


def test_chunk_pages_assigns_page_and_heading() -> None:
    pages = [
        {
            "page_no": 1,
            "blocks": [
                {
                    "text": "1 总则",
                    "bbox": [72, 100, 200, 120],
                    "size": 16,
                    "bold": True,
                },
                {
                    "text": "本标准规定了设备安全要求。" * 8,
                    "bbox": [72, 140, 500, 200],
                    "size": 12,
                    "bold": False,
                },
            ],
        },
        {
            "page_no": 2,
            "blocks": [
                {
                    "text": "2 范围",
                    "bbox": [72, 100, 200, 120],
                    "size": 16,
                    "bold": True,
                },
                {
                    "text": "适用于化工装置的运行与维护。" * 8,
                    "bbox": [72, 140, 500, 200],
                    "size": 12,
                    "bold": False,
                },
            ],
        },
    ]
    drafts = chunk_pages(pages, ChunkRules(min_tokens=10, max_tokens=400), title="测试手册")
    assert drafts
    assert all(d.page_start >= 1 for d in drafts)
    assert any("总则" in " ".join(d.heading_path) or "总则" in d.content for d in drafts)


def test_clause_mode_splits_on_clause_numbers() -> None:
    pages = [
        {
            "page_no": 1,
            "blocks": [
                {
                    "text": "4.1.1本条款规定操作步骤与注意事项，内容足够长以通过最小 token。" * 3,
                    "bbox": [72, 100, 500, 140],
                    "size": 12,
                },
                {
                    "text": "4.1.2后续条款继续描述安全要求与检查项目，同样需要足够长度。" * 3,
                    "bbox": [72, 160, 500, 200],
                    "size": 12,
                },
            ],
        }
    ]
    drafts = chunk_pages(
        pages,
        ChunkRules(min_tokens=5, max_tokens=200, clause_mode=True),
        title="规程",
    )
    assert len(drafts) >= 2
