"""请求级中间件：追踪标识与访问日志。"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.platform.logging import get_logger, request_id_var, tenant_id_var, user_id_var

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-Id"

# 探针噪音太大，成功时不记访问日志
_QUIET_PATHS = {"/healthz", "/readyz", "/metrics"}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        tenant_token = tenant_id_var.set(None)
        user_token = user_id_var.set(None)

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            self._log(request, 500, started)
            raise
        finally:
            request_id_var.reset(token)
            tenant_id_var.reset(tenant_token)
            user_id_var.reset(user_token)

        response.headers[REQUEST_ID_HEADER] = request_id
        self._log(request, response.status_code, started)
        return response

    @staticmethod
    def _log(request: Request, status_code: int, started: float) -> None:
        if request.url.path in _QUIET_PATHS and status_code < 400:
            return
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
