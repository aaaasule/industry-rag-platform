"""接入点凭证加解密与掩码。"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.platform.config import Settings, get_settings
from app.platform.errors import AppError


def _fernet(settings: Settings | None = None) -> Fernet:
    settings = settings or get_settings()
    secret = settings.resolved_credential_secret
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_credential(plaintext: str, settings: Settings | None = None) -> str:
    if not plaintext:
        return ""
    return _fernet(settings).encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_credential(cipher: str, settings: Settings | None = None) -> str:
    if not cipher:
        return ""
    try:
        return _fernet(settings).decrypt(cipher.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise AppError("凭证解密失败", code="credential_error") from exc


def credential_hint(plaintext: str) -> str:
    if not plaintext:
        return ""
    return plaintext[-3:] if len(plaintext) >= 3 else plaintext


def mask_credential(hint: str) -> str:
    if not hint:
        return "***"
    return f"***{hint}"
