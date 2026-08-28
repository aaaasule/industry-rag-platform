"""documents.enabled：禁用文档不参与检索

Revision ID: 0010_document_enabled
Revises: 0009_profile_code_reuse
Create Date: 2026-08-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_document_enabled"
down_revision: str | None = "0009_profile_code_reuse"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("documents", "enabled")
