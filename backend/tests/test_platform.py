"""平台层单元测试：ID、分页、口令与令牌。"""

from __future__ import annotations

import time
import uuid

import pytest

from app.platform.errors import TokenExpired, Unauthenticated
from app.platform.ids import timestamp_of, uuid7
from app.platform.pagination import (
    InvalidCursor,
    Page,
    PageParams,
    decode_cursor,
    encode_cursor,
)
from app.platform.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestUuid7:
    def test_version_and_variant(self) -> None:
        value = uuid7()
        assert value.version == 7
        assert (value.int >> 62) & 0b11 == 0b10

    def test_monotonic_across_milliseconds(self) -> None:
        first = uuid7()
        time.sleep(0.002)
        second = uuid7()
        # 时间有序是索引局部性的前提，也是游标分页能只用主键的依据
        assert first < second

    def test_timestamp_roundtrip(self) -> None:
        before = time.time()
        value = uuid7()
        assert before - 0.01 <= timestamp_of(value) <= time.time() + 0.01

    def test_rejects_non_v7(self) -> None:
        with pytest.raises(ValueError):
            timestamp_of(uuid.uuid4())

    def test_unique_within_same_millisecond(self) -> None:
        batch = {uuid7() for _ in range(2000)}
        assert len(batch) == 2000


class TestCursor:
    def test_roundtrip(self) -> None:
        value = uuid7()
        assert decode_cursor(encode_cursor(value)) == value

    def test_no_padding_characters(self) -> None:
        # 游标会出现在 URL 查询串里，不能带 '='
        assert "=" not in encode_cursor(uuid7())

    @pytest.mark.parametrize("bad", ["", "not-base64!!", "YWJj"])
    def test_rejects_malformed(self, bad: str) -> None:
        with pytest.raises(InvalidCursor):
            decode_cursor(bad)


class _Row:
    def __init__(self, id: uuid.UUID) -> None:
        self.id = id


class TestPage:
    def test_last_page_has_no_cursor(self) -> None:
        rows = [_Row(uuid7()) for _ in range(3)]
        page = Page.build(rows, PageParams(limit=5, after=None))
        assert len(page.items) == 3
        assert page.next_cursor is None

    def test_full_page_emits_cursor_and_drops_sentinel(self) -> None:
        rows = [_Row(uuid7()) for _ in range(4)]
        page = Page.build(rows, PageParams(limit=3, after=None))
        assert len(page.items) == 3
        assert page.next_cursor == encode_cursor(rows[2].id)

    def test_empty_page(self) -> None:
        page = Page.build([], PageParams(limit=10, after=None))
        assert page.items == []
        assert page.next_cursor is None


class TestPassword:
    def test_verify_roundtrip(self) -> None:
        hashed = hash_password("Correct-Horse-1")
        assert verify_password("Correct-Horse-1", hashed)
        assert not verify_password("wrong", hashed)

    def test_salted(self) -> None:
        assert hash_password("same") != hash_password("same")

    def test_malformed_hash_is_not_an_exception(self) -> None:
        # 库里出现脏数据时应判为验证失败，而不是 500
        assert not verify_password("x", "not-a-hash")


class TestToken:
    def test_access_roundtrip(self) -> None:
        user_id, tenant_id = uuid7(), uuid7()
        token, expires_at = create_token(
            user_id=user_id, tenant_id=tenant_id, role="admin", token_type="access"
        )
        claims = decode_token(token, expected_type="access")
        assert claims.user_id == user_id
        assert claims.tenant_id == tenant_id
        assert claims.role == "admin"
        assert claims.expires_at == expires_at.replace(microsecond=0)

    def test_type_confusion_rejected(self) -> None:
        # 用 refresh token 当 access 使会绕过短有效期设计
        token, _ = create_token(
            user_id=uuid7(), tenant_id=uuid7(), role="member", token_type="refresh"
        )
        with pytest.raises(Unauthenticated):
            decode_token(token, expected_type="access")

    def test_tampered_signature_rejected(self) -> None:
        token, _ = create_token(
            user_id=uuid7(), tenant_id=uuid7(), role="member", token_type="access"
        )
        head, payload, sig = token.split(".")
        with pytest.raises(Unauthenticated):
            decode_token(f"{head}.{payload}.{sig[:-2]}xx", expected_type="access")

    def test_expired_maps_to_dedicated_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.platform import security

        settings = security.get_settings()
        monkeypatch.setattr(settings, "access_token_ttl_minutes", -1)
        token, _ = create_token(
            user_id=uuid7(), tenant_id=uuid7(), role="member", token_type="access"
        )
        # 前端要靠 token_expired 区分"静默刷新"与"跳登录页"
        with pytest.raises(TokenExpired):
            decode_token(token, expected_type="access")
