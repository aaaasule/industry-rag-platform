"""摄取编排入口。"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import (
    DOC_PENDING,
    JOB_QUEUED,
    Chunk,
    Document,
    DocumentPage,
    IngestionJob,
)
from app.platform.errors import NotFound
from app.platform.ids import uuid7
from app.platform.logging import get_logger

logger = get_logger(__name__)


async def enqueue_ingest(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID,
    session: AsyncSession,
    *,
    force: bool = False,
) -> uuid.UUID:
    """创建 parse 阶段任务并投递 Celery。返回 job_id。"""
    doc = (
        await session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if doc is None:
        raise NotFound("文档不存在")

    doc.status = DOC_PENDING
    doc.error_code = None
    doc.error_detail = None
    if force:
        await session.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
        await session.execute(delete(Chunk).where(Chunk.document_id == document_id))

    job = IngestionJob(
        id=uuid7(),
        tenant_id=tenant_id,
        document_id=document_id,
        stage="parse",
        status=JOB_QUEUED,
        progress=0.0,
    )
    session.add(job)
    await session.flush()

    # 延迟导入，避免模块循环；本地无 worker 时仍可登记文档
    try:
        from app.modules.ingestion.tasks import parse_document

        async_result = parse_document.apply_async(
            kwargs={
                "document_id": str(document_id),
                "tenant_id": str(tenant_id),
                "job_id": str(job.id),
            },
            queue="ingest",
        )
        job.celery_task_id = async_result.id
    except Exception:
        logger.exception("celery_enqueue_failed", document_id=str(document_id))
        # 开发机未起 Redis/worker 时允许登记成功，状态停在 pending
        job.error_code = "enqueue_failed"
        job.error_detail = "Celery 投递失败，请确认 Redis 与 worker 已启动"

    await session.flush()
    return job.id
