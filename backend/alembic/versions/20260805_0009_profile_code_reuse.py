"""软删后允许复用 tenant profile code

Revision ID: 0009_profile_code_reuse
Revises: 0008_profile_soft_delete
Create Date: 2026-08-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009_profile_code_reuse"
down_revision: str | None = "0008_profile_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_industry_profiles_tenant_code")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_industry_profiles_tenant_code
        ON industry_profiles (tenant_id, code)
        WHERE tenant_id IS NOT NULL AND deleted_at IS NULL
        """
    )
    op.execute("DROP INDEX IF EXISTS uq_industry_profiles_builtin_code")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_industry_profiles_builtin_code
        ON industry_profiles (code)
        WHERE tenant_id IS NULL AND deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_industry_profiles_tenant_code")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_industry_profiles_tenant_code
        ON industry_profiles (tenant_id, code)
        WHERE tenant_id IS NOT NULL
        """
    )
    op.execute("DROP INDEX IF EXISTS uq_industry_profiles_builtin_code")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_industry_profiles_builtin_code
        ON industry_profiles (code)
        WHERE tenant_id IS NULL
        """
    )
