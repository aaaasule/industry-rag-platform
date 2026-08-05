from __future__ import annotations

from typing import Any

from app.platform.errors import UnprocessableState

_TYPE_CHECKERS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
}


def validate_document_metadata(meta: dict[str, Any], schema: dict[str, Any]) -> None:
    if not schema:
        return
    unknown = set(meta) - set(schema)
    if unknown:
        raise UnprocessableState(
            f"元数据含未声明字段: {', '.join(sorted(unknown))}",
            code="metadata_invalid",
        )
    for key, spec in schema.items():
        if not isinstance(spec, dict):
            continue
        required = bool(spec.get("required"))
        if key not in meta:
            if required:
                raise UnprocessableState(f"缺少必填元数据: {key}", code="metadata_invalid")
            continue
        typ = spec.get("type")
        checker = _TYPE_CHECKERS.get(typ) if isinstance(typ, str) else None
        if checker is not None and not checker(meta[key]):
            raise UnprocessableState(
                f"元数据字段 {key} 类型应为 {typ}",
                code="metadata_invalid",
            )
