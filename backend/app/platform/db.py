"""数据库引擎、会话与 ORM 基类。

租户隔离是"数据库 RLS + 应用层过滤"双保险（02 文档 §3）。这里负责第一层：
每个事务开始时把 `app.tenant_id` 写进会话变量，Postgres 的行级安全策略据此
过滤。应用层的显式 `where tenant_id = ...` 仍然要写——RLS 是兜底，不是借口。
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.platform.config import Settings, get_settings
from app.platform.ids import uuid7

# 显式命名约定，否则 Alembic 自动生成的迁移里约束名会随机变化，
# 导致同一份 schema 在不同环境产生不可比对的差异
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def init_engine(settings: Settings | None = None) -> AsyncEngine:
    global _engine, _sessionmaker
    settings = settings or get_settings()
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_pool_size,
        pool_pre_ping=True,
    )
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False, autoflush=False)
    return _engine


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        init_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def set_rls_context(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> None:
    """把租户/用户写入事务级会话变量，供 RLS 策略读取。

    set_config 的第三个参数为 true 表示 SET LOCAL：作用域限于当前事务，连接
    归还池子时自动失效，因此不会把上一个请求的租户泄漏给下一个请求。
    """
    await session.execute(
        text(
            "SELECT set_config('app.tenant_id', :t, true), "
            "       set_config('app.user_id', :u, true)"
        ),
        {"t": str(tenant_id) if tenant_id else "", "u": str(user_id) if user_id else ""},
    )


@asynccontextmanager
async def session_scope(
    tenant_id: uuid.UUID | None = None, user_id: uuid.UUID | None = None
) -> AsyncIterator[AsyncSession]:
    """给 Worker / 脚本用的会话上下文。HTTP 请求走 deps.get_session。"""
    async with get_sessionmaker()() as session:
        await set_rls_context(session, tenant_id=tenant_id, user_id=user_id)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
