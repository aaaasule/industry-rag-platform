"""知识库与文档摄取表

Revision ID: 0002_knowledge_ingestion
Revises: 0001_initial_identity
Create Date: 2026-07-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_knowledge_ingestion"
down_revision: str | None = "0001_initial_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 与 Settings.embedding_dim 默认值一致；换维度走新建知识库，不在此迁移里改列宽
EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.create_table(
        "industry_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "parse_rules",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "chunk_rules",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "metadata_schema",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "prompt_overrides",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "retrieval_rules",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name="fk_industry_profiles_tenant"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_industry_profiles"),
    )
    # PostgreSQL 中 UNIQUE (tenant_id, code) 对 NULL tenant_id 不去重，内置模板需 partial index
    op.execute(
        """
        CREATE UNIQUE INDEX uq_industry_profiles_builtin_code
        ON industry_profiles (code) WHERE tenant_id IS NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_industry_profiles_tenant_code
        ON industry_profiles (tenant_id, code) WHERE tenant_id IS NOT NULL
        """
    )

    op.create_table(
        "knowledge_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("embedding_dim", sa.Integer(), nullable=False),
        sa.Column("visibility", sa.Text(), nullable=False, server_default="private"),
        sa.Column(
            "settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("doc_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE", name="fk_kb_tenant"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["industry_profiles.id"], name="fk_kb_profile"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_kb_created_by"),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_bases"),
        sa.CheckConstraint(
            "visibility IN ('private', 'tenant')", name="ck_knowledge_bases_visibility"
        ),
    )
    op.create_index("ix_kb_tenant", "knowledge_bases", ["tenant_id"])

    op.create_table(
        "kb_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kb_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["kb_id"], ["knowledge_bases.id"], ondelete="CASCADE", name="fk_kb_grants_kb"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_kb_grants_user"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_kb_grants"),
        sa.UniqueConstraint("kb_id", "user_id", name="uq_kb_grants_kb_user"),
        sa.CheckConstraint(
            "permission IN ('read', 'write', 'manage')", name="ck_kb_grants_permission"
        ),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kb_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["kb_id"], ["knowledge_bases.id"], ondelete="CASCADE", name="fk_documents_kb"
        ),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], name="fk_documents_uploader"),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.CheckConstraint(
            "status IN ('pending','parsing','chunking','embedding','ready','failed')",
            name="ck_documents_status",
        ),
        sa.CheckConstraint(
            "source_type IN ('upload','url','sync')", name="ck_documents_source_type"
        ),
    )
    op.create_index(
        "uq_doc_checksum",
        "documents",
        ["kb_id", "checksum"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_doc_kb_status",
        "documents",
        ["kb_id", "status"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "document_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("blocks", postgresql.JSONB(), nullable=False),
        sa.Column("plain_text", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False, server_default="text"),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="CASCADE", name="fk_pages_document"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_pages"),
        sa.UniqueConstraint("document_id", "page_no", name="uq_document_pages_doc_page"),
    )

    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kb_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column(
            "heading_path",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("chunk_type", sa.Text(), nullable=False, server_default="text"),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column(
            "bboxes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("tsv", postgresql.TSVECTOR(), nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="CASCADE", name="fk_chunks_document"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
        sa.UniqueConstraint("document_id", "seq", name="uq_chunks_document_seq"),
    )
    op.execute(
        """
        CREATE INDEX idx_chunks_embedding ON chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )
    op.create_index("idx_chunks_tsv", "chunks", ["tsv"], postgresql_using="gin")
    op.create_index("idx_chunks_kb", "chunks", ["kb_id"])
    op.create_index("idx_chunks_doc", "chunks", ["document_id", "seq"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("celery_task_id", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="CASCADE", name="fk_jobs_document"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_jobs"),
        sa.CheckConstraint("stage IN ('parse','chunk','embed')", name="ck_jobs_stage"),
        sa.CheckConstraint(
            "status IN ('queued','running','succeeded','failed')", name="ck_jobs_status"
        ),
    )
    op.create_index("idx_jobs_doc", "ingestion_jobs", ["document_id", "created_at"])

    _enable_tenant_rls(
        [
            "industry_profiles",
            "knowledge_bases",
            "kb_grants",
            "documents",
            "document_pages",
            "chunks",
            "ingestion_jobs",
        ]
    )


def downgrade() -> None:
    for table in (
        "ingestion_jobs",
        "chunks",
        "document_pages",
        "documents",
        "kb_grants",
        "knowledge_bases",
        "industry_profiles",
    ):
        op.drop_table(table)


def _enable_tenant_rls(tables: list[str]) -> None:
    """共享库多租户：按 app.tenant_id 隔离。

    industry_profiles 额外允许 tenant_id IS NULL（系统内置模板对所有租户只读可见）。
    """
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        if table == "industry_profiles":
            # 内置模板 tenant_id IS NULL，对所有租户只读可见；租户可写自己的副本
            using = "(tenant_id IS NULL OR tenant_id = app_current_tenant())"
            check = "(tenant_id IS NULL OR tenant_id = app_current_tenant())"
        else:
            using = "(tenant_id = app_current_tenant())"
            check = using
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING {using}
            WITH CHECK {check}
            """
        )
