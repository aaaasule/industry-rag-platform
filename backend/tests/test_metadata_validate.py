import pytest
from app.modules.knowledge.metadata_validate import validate_document_metadata
from app.platform.errors import UnprocessableState


def test_empty_schema_allows_anything() -> None:
    validate_document_metadata({"x": 1}, {})


def test_rejects_unknown_key() -> None:
    schema = {"equipment_model": {"type": "string"}}
    with pytest.raises(UnprocessableState) as ei:
        validate_document_metadata({"equipment_model": "A", "extra": 1}, schema)
    assert ei.value.code == "metadata_invalid"


def test_required_missing() -> None:
    schema = {"equipment_model": {"type": "string", "required": True}}
    with pytest.raises(UnprocessableState):
        validate_document_metadata({}, schema)


def test_type_mismatch() -> None:
    schema = {"n": {"type": "number"}}
    with pytest.raises(UnprocessableState):
        validate_document_metadata({"n": "x"}, schema)


def test_valid_passes() -> None:
    schema = {
        "equipment_model": {"type": "string", "required": True},
        "flag": {"type": "boolean"},
    }
    validate_document_metadata({"equipment_model": "HYD-2201", "flag": True}, schema)
