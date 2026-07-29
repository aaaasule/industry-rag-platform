"""口令哈希与 JWT 签发/校验。

JWT 里带 `tid`（租户），租户上下文只能来自 token，永远不接受客户端参数——
这是多租户越权最常见的入口（03 文档 §1）。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.platform.config import Settings, get_settings
from app.platform.errors import TokenExpired, Unauthenticated
from app.platform.ids import uuid7

_hasher = PasswordHasher()

TokenType = Literal["access", "refresh"]


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, raw)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """Argon2 参数升级后，用户下次成功登录时顺带迁移。"""
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True


@dataclass(frozen=True, slots=True)
class TokenClaims:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str
    token_type: TokenType
    jti: uuid.UUID
    expires_at: datetime


def create_token(
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: str,
    token_type: TokenType,
    settings: Settings | None = None,
) -> tuple[str, datetime]:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    ttl = (
        timedelta(minutes=settings.access_token_ttl_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_ttl_days)
    )
    expires_at = now + ttl
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "role": role,
        "typ": token_type,
        "jti": str(uuid7()),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_at


def decode_token(
    token: str,
    *,
    expected_type: TokenType,
    settings: Settings | None = None,
) -> TokenClaims:
    settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpired() from exc
    except jwt.PyJWTError as exc:
        raise Unauthenticated("令牌无效") from exc

    if payload.get("typ") != expected_type:
        raise Unauthenticated("令牌类型不匹配")

    try:
        return TokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            tenant_id=uuid.UUID(payload["tid"]),
            role=payload["role"],
            token_type=expected_type,
            jti=uuid.UUID(payload["jti"]),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except (KeyError, ValueError) as exc:
        raise Unauthenticated("令牌结构异常") from exc
