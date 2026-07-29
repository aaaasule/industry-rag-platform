"""模型接入点表

Revision ID: 0006_model_connections
Revises: 0005_audit_logs
Create Date: 2026-07-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_model_connections"
down_revision: str | None = "0005_audit_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("provider_type", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("credential_cipher", sa.Text(), nullable=False, server_default=""),
        sa.Column("credential_hint", sa.Text(), nullable=False, server_default=""),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("purposes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("health", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("health_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "extra",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
            name="fk_model_connections_tenant",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_model_connections"),
        sa.CheckConstraint(
            "provider_type IN ('openai_compatible','fake')",
            name="ck_model_connections_provider_type",
        ),
        sa.CheckConstraint(
            "health IN ('healthy','degraded','down','unknown')",
            name="ck_model_connections_health",
        ),
    )
    op.create_index(
        "idx_conn_route",
        "model_connections",
        ["tenant_id", "enabled", "priority"],
        postgresql_where=sa.text("enabled"),
    )

    op.execute("ALTER TABLE model_connections ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE model_connections FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY model_connections_tenant_isolation ON model_connections
        USING (tenant_id IS NULL OR tenant_id = app_current_tenant())
        WITH CHECK (tenant_id = app_current_tenant())
        """
    )


def downgrade() -> None:
    op.drop_table("model_connections")
