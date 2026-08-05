"""industry_profiles 软删除 deleted_at

Revision ID: 0008_profile_soft_delete
Revises: 0007_llm_usages
Create Date: 2026-08-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_profile_soft_delete"
down_revision: str | None = "0007_llm_usages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "industry_profiles",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("industry_profiles", "deleted_at")
