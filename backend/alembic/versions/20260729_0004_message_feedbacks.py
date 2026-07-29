"""消息反馈表

Revision ID: 0004_message_feedbacks
Revises: 0003_chat_conversations
Create Date: 2026-07-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_message_feedbacks"
down_revision: str | None = "0003_chat_conversations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "message_feedbacks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            ondelete="CASCADE",
            name="fk_message_feedbacks_message",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_message_feedbacks_user",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_message_feedbacks"),
        sa.UniqueConstraint("message_id", "user_id", name="uq_message_feedbacks_msg_user"),
        sa.CheckConstraint("rating IN ('up','down')", name="ck_message_feedbacks_rating"),
        sa.CheckConstraint(
            "reason IS NULL OR reason IN ('irrelevant','bad_citation','other')",
            name="ck_message_feedbacks_reason",
        ),
    )
    op.create_index("idx_message_feedbacks_message", "message_feedbacks", ["message_id"])

    _enable_tenant_rls(["message_feedbacks"])


def downgrade() -> None:
    op.drop_table("message_feedbacks")


def _enable_tenant_rls(tables: list[str]) -> None:
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        using = "(tenant_id = app_current_tenant())"
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING {using}
            WITH CHECK {using}
            """
        )
