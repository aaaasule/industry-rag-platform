"""SSE 事件序列化。"""

from __future__ import annotations

import json
from typing import Any


def sse_event(event: str, data: dict[str, Any]) -> bytes:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n".encode()
