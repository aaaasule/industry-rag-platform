"""Alembic 运行环境。

连接串统一从应用配置读取，不在 alembic.ini 里再写一份——两份配置迟早会
不一致，而且 ini 里放密码会进版本库。
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 导入所有模型，让 Base.metadata 完整，autogenerate 才能正确比对
from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.chat import models as chat_models  # noqa: F401
from app.modules.identity import models as identity_models  # noqa: F401
from app.modules.knowledge import models as knowledge_models  # noqa: F401
from app.modules.modelops import models as modelops_models  # noqa: F401
from app.platform.config import get_settings
from app.platform.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_settings = get_settings()
# 迁移用属主角色（需要 DDL 权限），应用运行时用受 RLS 约束的 irp_app
config.set_main_option("sqlalchemy.url", _settings.database_migration_url or _settings.database_url)

target_metadata = Base.metadata


def _include_object(obj, name, type_, reflected, compare_to) -> bool:  # type: ignore[no-untyped-def]
    # 分区表的子分区由迁移脚本显式管理，不参与 autogenerate 比对
    return not (type_ == "table" and name and "_p20" in name)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
