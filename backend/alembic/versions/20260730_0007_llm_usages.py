"""用量与定价表

Revision ID: 0007_llm_usages
Revises: 0006_model_connections
Create Date: 2026-07-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_llm_usages"
down_revision: str | None = "0006_model_connections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_pricing",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_type", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("prompt_price_per_1k", sa.Numeric(12, 6), nullable=False),
        sa.Column("completion_price_per_1k", sa.Numeric(12, 6), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False, server_default="USD"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_model_pricing"),
        sa.UniqueConstraint(
            "provider_type",
            "model",
            "effective_from",
            name="uq_model_pricing_provider_model_from",
        ),
    )

    op.create_table(
        "llm_usages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kb_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("provider_type", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("currency", sa.Text(), nullable=False, server_default="USD"),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_llm_usages"),
        sa.CheckConstraint(
            "purpose IN ('chat','embedding','rerank','title')",
            name="ck_llm_usages_purpose",
        ),
    )
    op.create_index(
        "idx_usage_tenant_time",
        "llm_usages",
        ["tenant_id", sa.text("created_at DESC")],
    )

    # connection_id 用全零 UUID 表示「无接入点」，避免主键含 NULL
    op.create_table(
        "llm_usage_hourlies",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bucket_hour", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prompt_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cost", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("latency_p95_ms", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint(
            "tenant_id",
            "bucket_hour",
            "model",
            "purpose",
            "connection_id",
            name="pk_llm_usage_hourlies",
        ),
    )
    op.create_index(
        "idx_hourly_range",
        "llm_usage_hourlies",
        ["tenant_id", sa.text("bucket_hour DESC")],
    )

    _enable_tenant_rls(["llm_usages", "llm_usage_hourlies"])
    # model_pricing 全局只读表，无 tenant_id，不启 RLS


def downgrade() -> None:
    op.drop_table("llm_usage_hourlies")
    op.drop_table("llm_usages")
    op.drop_table("model_pricing")


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
