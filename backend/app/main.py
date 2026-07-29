"""FastAPI 应用装配。

这个文件只负责"组装"，不含任何业务逻辑。判断标准：新增一个业务模块时，
这里最多只应该在 api.py 里加一行 include_router，本文件不动。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.health import router as health_router
from app.platform.config import get_settings
from app.platform.db import dispose_engine, init_engine
from app.platform.errors import register_exception_handlers
from app.platform.llm.factory import (
    build_embedding_provider,
    build_llm_provider,
    build_rerank_provider,
    close_providers,
)
from app.platform.logging import configure_logging, get_logger
from app.platform.middleware import RequestContextMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    init_engine(settings)

    # Provider 在启动时构造一次并挂到 app.state：连接池得以复用，
    # 且测试可以通过覆盖 state 注入 Fake 而不必打补丁
    app.state.llm = build_llm_provider(settings)
    app.state.embedding = build_embedding_provider(settings)
    app.state.rerank = build_rerank_provider(settings)

    logger.info(
        "app_started",
        environment=settings.environment,
        llm_provider=settings.llm_provider,
        embedding_dim=settings.embedding_dim,
    )
    try:
        yield
    finally:
        await close_providers(settings)
        await dispose_engine()
        logger.info("app_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)

    app = FastAPI(
        title="工业知识库平台",
        version="0.1.0",
        docs_url="/docs" if settings.is_local else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.is_local else None,
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
