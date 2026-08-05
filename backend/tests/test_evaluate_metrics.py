from app.modules.retrieval.eval_metrics import relevant_rank


def test_relevant_rank_by_id() -> None:
    hits = [{"document_id": "a"}, {"document_id": "b"}]
    assert relevant_rank(hits, {"expected_document_ids": ["b"]}) == 2


def test_relevant_rank_by_title() -> None:
    hits = [{"document_id": "x", "document_title": "Hydraulic Manual v2"}]
    assert relevant_rank(hits, {"expected_document_titles": ["hydraulic"]}) == 1


def test_relevant_rank_no_label() -> None:
    hits = [{"document_id": "a"}]
    assert relevant_rank(hits, {}) is None


def test_relevant_rank_not_found() -> None:
    hits = [{"document_id": "a"}]
    assert relevant_rank(hits, {"expected_document_ids": ["missing"]}) is None
