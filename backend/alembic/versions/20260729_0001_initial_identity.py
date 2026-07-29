"""首个迁移：扩展、租户/用户/成员表、RLS 策略

Revision ID: 0001_initial_identity
Revises:
Create Date: 2026-07-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial_identity"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    _create_rls_helpers()

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column(
            "quota", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_tenants"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
        sa.CheckConstraint("status IN ('active', 'suspended')", name="ck_tenants_status"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=True),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("status IN ('active', 'suspended')", name="ck_users_status"),
    )

    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_memberships"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_memberships_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_memberships_user_id_users", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_memberships_tenant_id"),
        sa.CheckConstraint("role IN ('owner', 'admin', 'member')", name="ck_memberships_role"),
    )
    op.create_index("ix_memberships_tenant_id", "memberships", ["tenant_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])

    _enable_membership_rls()
    _grant_app_role()


def downgrade() -> None:
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("tenants")
    op.execute("DROP FUNCTION IF EXISTS app_current_user()")
    op.execute("DROP FUNCTION IF EXISTS app_current_tenant()")


def _create_rls_helpers() -> None:
    """RLS 策略读取的会话变量访问器。

    直接在策略里写 current_setting(...)::uuid 会在变量为空串时抛类型错误，
    统一收敛到这两个函数，策略本身保持可读。STABLE 让规划器可以缓存结果。
    """
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_tenant() RETURNS uuid
        LANGUAGE sql STABLE AS $$
            SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_user() RETURNS uuid
        LANGUAGE sql STABLE AS $$
            SELECT NULLIF(current_setting('app.user_id', true), '')::uuid
        $$
        """
    )


def _enable_membership_rls() -> None:
    """memberships 的行级安全。

    双键策略：按租户可见（业务请求路径），或按用户可见（登录尚未确定租户时，
    需要列出"我能进哪些租户"）。两个变量都为空时函数返回 NULL，等值比较为
    NULL，策略拒绝所有行——默认关闭，符合最小权限。

    FORCE 是必需的：不加的话表属主（也就是应用连接用的角色）会绕过策略，
    RLS 形同虚设。

    tenants 与 users 不加 RLS：前者是租户注册表本身，后者是跨租户的全局用户
    （02 文档 §4.1），它们的访问收敛在 identity 模块内部由应用层控制。
    """
    op.execute("ALTER TABLE memberships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memberships FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY memberships_tenant_isolation ON memberships
        USING (
            tenant_id = app_current_tenant()
            OR user_id = app_current_user()
        )
        WITH CHECK (tenant_id = app_current_tenant())
        """
    )


APP_ROLE = "irp_app"


def _grant_app_role() -> None:
    """给应用角色授权。

    迁移以属主/超级用户身份执行，应用则以 irp_app 连接——超级用户绕过 RLS，
    所以这个角色分离不是洁癖，而是隔离生效的前提。

    ALTER DEFAULT PRIVILEGES 让后续迁移新建的表自动获得同样的授权，
    避免每加一张表就要记得补一条 GRANT。
    """
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
                CREATE ROLE {APP_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS;
            END IF;
        END
        $$
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE}")
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE}"
    )
