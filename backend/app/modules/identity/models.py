"""身份与租户的 ORM 模型（02 文档 §4.1）。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.db import Base, TimestampMixin, UUIDPrimaryKeyMixin

# SQLite（单测）没有 JSONB / CITEXT，退化为等价类型
JSONColumn = JSONB().with_variant(JSON(), "sqlite")
EmailColumn = CITEXT().with_variant(String(320), "sqlite")

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
ROLES = (ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER)

# 角色权限是包含关系，用序数做比较，避免到处写 role in (...) 的散装判断
ROLE_RANK = {ROLE_MEMBER: 0, ROLE_ADMIN: 1, ROLE_OWNER: 2}


def role_at_least(role: str, required: str) -> bool:
    return ROLE_RANK.get(role, -1) >= ROLE_RANK[required]


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    quota: Mapped[dict[str, Any]] = mapped_column(JSONColumn, nullable=False, default=dict)

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status == "active"


class User(UUIDPrimaryKeyMixin, Base):
    """全局表：一个人可属于多个租户，因此这里不加 RLS，也没有 tenant_id。"""

    __tablename__ = "users"

    # citext：邮箱大小写不敏感的唯一性由数据库保证，不依赖应用层记得转小写
    email: Mapped[str] = mapped_column(EmailColumn, unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status == "active"


class Membership(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tenant: Mapped[Tenant] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")
