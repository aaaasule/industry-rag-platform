"""jieba 用户词典：按词表指纹缓存，避免重复 load_userdict。"""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Sequence

_fingerprint: str | None = None


def ensure_jieba_userdict(words: Sequence[str]) -> None:
    global _fingerprint
    cleaned = sorted({w.strip() for w in words if w and str(w).strip()})
    if not cleaned:
        return
    fp = hashlib.sha256("\n".join(cleaned).encode()).hexdigest()
    if fp == _fingerprint:
        return
    import jieba

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
        for w in cleaned:
            f.write(f"{w}\n")
        path = f.name
    try:
        jieba.load_userdict(path)
    finally:
        os.unlink(path)
    _fingerprint = fp
