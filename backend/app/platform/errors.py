"""统一异常与错误响应。

03 文档约定：错误响应必须是结构化的，`code` 是稳定的机器可读标识，`message`
面向用户。前端只允许对 code 做逻辑判断，绝不解析 message。
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.platform.logging import get_logger, request_id_var

logger = get_logger(__name__)


class AppError(Exception):
    """业务异常基类。所有可预期的失败都应抛它的子类，而不是裸 HTTPException。"""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "bad_request"
    message: str = "请求无法处理"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        code: str | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details or {}
        if code:
            self.code = code
        super().__init__(self.message)


class Unauthenticated(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthenticated"
    message = "未认证或登录已过期"


class TokenExpired(Unauthenticated):
    code = "token_expired"
    message = "登录已过期，请重新登录"


class Forbidden(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"
    message = "没有权限执行该操作"


class NotFound(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "资源不存在"


class Conflict(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    message = "资源状态冲突"


class UnprocessableState(AppError):
    # 用字面量而非 status 常量：Starlette 在 422 的常量命名上做过一次改名，
    # 引用常量会在不同版本间产生弃用告警
    status_code = 422
    code = "unprocessable_state"
    message = "当前状态下无法执行该操作"


class RateLimited(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"
    message = "请求过于频繁，请稍后重试"


class ProviderUnavailable(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "provider_unavailable"
    message = "上游模型服务暂时不可用"


def _payload(code: str, message: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id_var.get(),
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {
                "field": ".".join(str(p) for p in err["loc"][1:]) or str(err["loc"][0]),
                "reason": err["msg"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_payload("validation_error", "请求参数校验失败", {"fields": fields}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "unauthenticated", 403: "forbidden", 404: "not_found"}.get(
            exc.status_code, "http_error"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(code, str(exc.detail), {}),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        # 未预期的异常一律记完整堆栈，但只向外暴露 request_id，不泄露内部结构
        logger.exception("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_payload("internal_error", "服务内部错误", {}),
        )
