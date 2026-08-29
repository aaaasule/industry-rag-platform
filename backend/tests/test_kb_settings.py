"""KB settings PATCH / GET effective 规则出站。"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.modules.knowledge.settings_validate import (
    shallow_merge_settings,
    validate_kb_settings,
)
from app.modules.profile.schemas import DEFAULT_RETRIEVAL_RULES
from app.modules.profile.service import merge_retrieval_rules
from app.platform.errors import UnprocessableState
from tests.conftest import Fixture


def test_validate_kb_settings_rejects_unknown_top_level() -> None:
    with pytest.raises(UnprocessableState) as ei:
        validate_kb_settings({"prompt_overrides": {"system": "x"}})
    assert ei.value.code == "settings_invalid"


def test_validate_kb_settings_rejects_unknown_nested() -> None:
    with pytest.raises(UnprocessableState) as ei:
        validate_kb_settings({"chunk_rules": {"max_tokens": 256, "foo": 1}})
    assert ei.value.code == "settings_invalid"


def test_validate_kb_settings_rejects_invalid_chunk_value_type() -> None:
    with pytest.raises(UnprocessableState) as ei:
        validate_kb_settings({"chunk_rules": {"max_tokens": "abc"}})
    assert ei.value.code == "settings_invalid"


def test_validate_kb_settings_rejects_invalid_retrieval_value_type() -> None:
    with pytest.raises(UnprocessableState) as ei:
        validate_kb_settings({"retrieval_rules": {"top_k": "not-a-number"}})
    assert ei.value.code == "settings_invalid"


def test_validate_kb_settings_allows_whitelist() -> None:
    out = validate_kb_settings(
        {
            "chunk_rules": {"max_tokens": 256},
            "retrieval_rules": {"top_k": 5, "query_expand": True},
        }
    )
    assert out["chunk_rules"]["max_tokens"] == 256
    assert out["retrieval_rules"]["query_expand"] is True


def test_shallow_merge_settings_preserves_other_domain() -> None:
    existing = {
        "chunk_rules": {"max_tokens": 256},
        "retrieval_rules": {"top_k": 12, "query_expand": True},
    }
    incoming = validate_kb_settings({"chunk_rules": {"min_tokens": 40}})
    merged = shallow_merge_settings(existing, incoming)
    assert merged["chunk_rules"] == {"max_tokens": 256, "min_tokens": 40}
    assert merged["retrieval_rules"] == {"top_k": 12, "query_expand": True}


def test_query_expand_defaults_false() -> None:
    assert DEFAULT_RETRIEVAL_RULES.query_expand is False
    cfg = merge_retrieval_rules(profile_rules=None, kb_settings=None)
    assert cfg.query_expand is False
    cfg2 = merge_retrieval_rules(
        profile_rules=None,
        kb_settings={"retrieval_rules": {"query_expand": True}},
    )
    assert cfg2.query_expand is True


async def test_patch_kb_settings_effective_chunk_rules(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    create = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "settings 库", "visibility": "private"},
    )
    assert create.status_code == 201, create.text
    kb_id = create.json()["id"]
    assert "settings" in create.json()
    assert "effective_chunk_rules" in create.json()
    assert "effective_retrieval_rules" in create.json()

    patched = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=auth_headers,
        json={"settings": {"chunk_rules": {"max_tokens": 256}}},
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["settings"]["chunk_rules"]["max_tokens"] == 256
    assert body["effective_chunk_rules"]["max_tokens"] == 256

    got = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=auth_headers)
    assert got.status_code == 200, got.text
    assert got.json()["effective_chunk_rules"]["max_tokens"] == 256
    assert got.json()["effective_retrieval_rules"]["query_expand"] is False


async def test_patch_kb_settings_unknown_key_422(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    create = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "非法 settings"},
    )
    assert create.status_code == 201, create.text
    kb_id = create.json()["id"]

    bad = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=auth_headers,
        json={"settings": {"chunk_rules": {"max_tokens": 256, "unknown": True}}},
    )
    assert bad.status_code == 422, bad.text
    assert bad.json()["error"]["code"] == "settings_invalid"


async def test_patch_kb_settings_invalid_value_422_preserves_prior(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    create = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "值类型校验库"},
    )
    assert create.status_code == 201, create.text
    kb_id = create.json()["id"]

    good = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=auth_headers,
        json={"settings": {"chunk_rules": {"max_tokens": 256}}},
    )
    assert good.status_code == 200, good.text
    assert good.json()["effective_chunk_rules"]["max_tokens"] == 256

    bad = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=auth_headers,
        json={"settings": {"chunk_rules": {"max_tokens": "abc"}}},
    )
    assert bad.status_code == 422, bad.text
    assert bad.json()["error"]["code"] == "settings_invalid"

    got = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=auth_headers)
    assert got.status_code == 200, got.text
    assert got.json()["settings"]["chunk_rules"]["max_tokens"] == 256
    assert got.json()["effective_chunk_rules"]["max_tokens"] == 256


async def test_patch_kb_settings_shallow_merge_preserves_retrieval(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    create = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "浅合并库"},
    )
    assert create.status_code == 201, create.text
    kb_id = create.json()["id"]

    first = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=auth_headers,
        json={
            "settings": {
                "chunk_rules": {"max_tokens": 256},
                "retrieval_rules": {"top_k": 12, "query_expand": True},
            }
        },
    )
    assert first.status_code == 200, first.text

    second = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=auth_headers,
        json={"settings": {"chunk_rules": {"min_tokens": 40}}},
    )
    assert second.status_code == 200, second.text
    settings = second.json()["settings"]
    assert settings["chunk_rules"]["max_tokens"] == 256
    assert settings["chunk_rules"]["min_tokens"] == 40
    assert settings["retrieval_rules"]["top_k"] == 12
    assert settings["retrieval_rules"]["query_expand"] is True