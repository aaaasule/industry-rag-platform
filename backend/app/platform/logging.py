"""结构化日志。

05 文档约定字段固定：ts / level / logger / message / request_id / tenant_id /
user_id / duration_ms / error_code。request_id 通过 ContextVar 贯穿整个请求，
无需在每层函数签名里传递。

禁止把文档正文、提示词全文写入日志，只记 hash 与长度。
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from contextvars import ContextVar
from typing import Any

import structlog

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def _inject_context(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for key, var in (
        ("request_id", request_id_var),
        ("tenant_id", tenant_id_var),
        ("user_id", user_id_var),
    ):
        value = var.get()
        if value:
            event_dict[key] = value
    return event_dict


def configure_logging(level: str = "INFO", fmt: str = "console") -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())

    renderer: Any = (
        structlog.processors.JSONRenderer(ensure_ascii=False)
        if fmt == "json"
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
            _inject_context,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[level.upper()]
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
