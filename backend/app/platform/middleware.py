"""请求级中间件：追踪标识与访问日志。

使用纯 ASGI 实现，避免 BaseHTTPMiddleware 缓冲 StreamingResponse（SSE 会被攒成一整包）。
"""

from __future__ import annotations

import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.platform.logging import get_logger, request_id_var, tenant_id_var, user_id_var

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-Id"
_REQUEST_ID_HEADER_BYTES = b"x-request-id"

# 探针噪音太大，成功时不记访问日志
_QUIET_PATHS = {"/healthz", "/readyz", "/metrics"}


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers") or []
        request_id = _header_value(headers, _REQUEST_ID_HEADER_BYTES) or str(uuid.uuid4())
        path = scope.get("path") or ""
        method = scope.get("method") or "GET"

        token = request_id_var.set(request_id)
        tenant_token = tenant_id_var.set(None)
        user_token = user_id_var.set(None)
        started = time.perf_counter()
        status_code = 500
        logged = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, logged
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", 500))
                raw_headers: list[tuple[bytes, bytes]] = list(message.get("headers") or [])
                raw_headers = [
                    (k, v) for k, v in raw_headers if k.lower() != _REQUEST_ID_HEADER_BYTES
                ]
                raw_headers.append((_REQUEST_ID_HEADER_BYTES, request_id.encode("latin-1")))
                message = {**message, "headers": raw_headers}
                await send(message)
                return

            if message["type"] == "http.response.body" and not message.get("more_body", False):
                if not logged:
                    _log(method, path, status_code, started)
                    logged = True

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            if not logged:
                _log(method, path, status_code, started)
                logged = True
        except Exception:
            if not logged:
                _log(method, path, 500, started)
                logged = True
            raise
        finally:
            request_id_var.reset(token)
            tenant_id_var.reset(tenant_token)
            user_id_var.reset(user_token)


def _header_value(headers: list[tuple[bytes, bytes]], name: bytes) -> str | None:
    for key, value in headers:
        if key.lower() == name:
            return value.decode("latin-1")
    return None


def _log(method: str, path: str, status_code: int, started: float) -> None:
    if path in _QUIET_PATHS and status_code < 400:
        return
    logger.info(
        "http_request",
        method=method,
        path=path,
        status=status_code,
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )
