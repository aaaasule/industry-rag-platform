"""摄取 Celery 任务。

解析调度单位在函数层是「页」（parse_one_page / ocr_page），文档任务内循环调用。
未来可改为 Celery group 页级并行（R1c），接口保持不变。

HTTP 登记文档后才 commit，Celery 可能抢跑；任务对 missing 做短暂重试。
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select

from app.modules.ingestion.chunkers.structure import chunk_pages
from app.modules.ingestion.chunkers.tsv import build_tsv
from app.modules.ingestion.parsers.layout import strip_headers_footers
from app.modules.ingestion.parsers.pdf import PageParse, parse_pdf_bytes
from app.modules.knowledge.models import (
    DOC_CHUNKING,
    DOC_EMBEDDING,
    DOC_FAILED,
    DOC_PARSING,
    DOC_READY,
    JOB_FAILED,
    JOB_RUNNING,
    JOB_SUCCEEDED,
    Chunk,
    Document,
    DocumentPage,
    IngestionJob,
    KnowledgeBase,
)
from app.modules.profile.service import resolve_effective_profile, to_ingestion_chunk_rules
from app.platform.config import get_settings
from app.platform.db import init_engine, session_scope
from app.platform.ids import uuid7
from app.platform.logging import get_logger
from app.platform.storage.object_store import S3ObjectStore
from app.worker import celery_app

logger = get_logger(__name__)


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


@celery_app.task(name="ingest.parse_document", bind=True, max_retries=5, default_retry_delay=2)
def parse_document(self: Any, document_id: str, tenant_id: str, job_id: str) -> str:
    try:
        return _run(
            _parse_document(uuid.UUID(document_id), uuid.UUID(tenant_id), uuid.UUID(job_id))
        )
    except _MissingRow:
        raise self.retry(countdown=2) from None


@celery_app.task(name="ingest.embed_document", bind=True, max_retries=5, default_retry_delay=2)
def embed_document(self: Any, document_id: str, tenant_id: str, job_id: str) -> str:
    try:
        return _run(
            _embed_document(uuid.UUID(document_id), uuid.UUID(tenant_id), uuid.UUID(job_id))
        )
    except _MissingRow:
        raise self.retry(countdown=2) from None


class _MissingRow(Exception):
    """事务尚未提交，稍后重试。"""


async def _parse_document(document_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> str:
    settings = get_settings()
    init_engine(settings)

    next_embed: tuple[uuid.UUID, uuid.UUID, uuid.UUID] | None = None

    async with session_scope(tenant_id=tenant_id) as session:
        job = await session.get(IngestionJob, job_id)
        doc = await session.get(Document, document_id)
        if job is None or doc is None:
            raise _MissingRow()

        job.status = JOB_RUNNING
        job.started_at = datetime.now(UTC)
        job.attempt += 1
        doc.status = DOC_PARSING
        await session.flush()

        try:
            store = S3ObjectStore(settings)
            data = await asyncio.to_thread(store.get, doc.storage_key)
            pages = await asyncio.to_thread(_parse_all_pages, data, doc.mime_type)
            page_dicts = [
                {
                    "page_no": p.page_no,
                    "width": p.width,
                    "height": p.height,
                    "blocks": p.blocks,
                    "plain_text": p.plain_text,
                    "source": p.source,
                }
                for p in pages
            ]
            page_dicts = strip_headers_footers(page_dicts)

            await session.execute(
                delete(DocumentPage).where(DocumentPage.document_id == document_id)
            )
            for p in page_dicts:
                session.add(
                    DocumentPage(
                        id=uuid7(),
                        tenant_id=tenant_id,
                        document_id=document_id,
                        page_no=p["page_no"],
                        width=p["width"],
                        height=p["height"],
                        blocks=p["blocks"],
                        plain_text=p["plain_text"],
                        source=p.get("source", "text"),
                    )
                )
            doc.page_count = len(page_dicts)
            doc.status = DOC_CHUNKING
            job.status = JOB_SUCCEEDED
            job.progress = 1.0
            job.finished_at = datetime.now(UTC)

            next_job = IngestionJob(
                id=uuid7(),
                tenant_id=tenant_id,
                document_id=document_id,
                stage="embed",
                status="queued",
            )
            session.add(next_job)
            await session.flush()
            next_embed = (document_id, tenant_id, next_job.id)
        except Exception as exc:
            logger.exception("parse_failed", document_id=str(document_id))
            doc.status = DOC_FAILED
            doc.error_code = "parse_failed"
            doc.error_detail = str(exc)[:2000]
            job.status = JOB_FAILED
            job.error_code = "parse_failed"
            job.error_detail = str(exc)[:2000]
            job.finished_at = datetime.now(UTC)
            return "failed"

    if next_embed is not None:
        doc_id, tid, jid = next_embed
        async_result = embed_document.apply_async(
            kwargs={
                "document_id": str(doc_id),
                "tenant_id": str(tid),
                "job_id": str(jid),
            },
            queue="embed",
        )
        async with session_scope(tenant_id=tid) as session:
            job = await session.get(IngestionJob, jid)
            if job is not None:
                job.celery_task_id = async_result.id
        return "parsed"
    return "failed"


def _parse_all_pages(data: bytes, mime_type: str) -> list[PageParse]:
    if "pdf" not in mime_type.lower() and not data[:5].startswith(b"%PDF"):
        from app.modules.ingestion.parsers.normalize import normalize

        plain = normalize(data.decode("utf-8", errors="ignore"))
        return [
            PageParse(
                page_no=1,
                width=595,
                height=842,
                blocks=[
                    {
                        "type": "paragraph",
                        "level": 0,
                        "text": plain,
                        "bbox": [72, 72, 523, 800],
                        "order": 0,
                        "size": 12,
                        "bold": False,
                    }
                ],
                plain_text=plain,
                source="text",
                needs_ocr=False,
            )
        ]

    pages = parse_pdf_bytes(data)
    if not any(p.needs_ocr for p in pages):
        return pages

    try:
        import pymupdf as fitz
    except ImportError:  # pragma: no cover
        import fitz  # type: ignore[no-redef]
    from app.modules.ingestion.parsers.ocr import ocr_page

    doc = fitz.open(stream=data, filetype="pdf")
    try:
        out: list[PageParse] = []
        for p in pages:
            out.append(ocr_page(doc[p.page_no - 1]) if p.needs_ocr else p)
        return out
    finally:
        doc.close()


async def _embed_document(document_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> str:
    settings = get_settings()
    init_engine(settings)

    async with session_scope(tenant_id=tenant_id) as session:
        from app.modules.modelops.provider_factory import ProviderFactory
        from app.platform.llm.factory import aclose_provider

        # Celery 每次 asyncio.run 新建 loop；禁止跨任务复用 httpx.AsyncClient
        embedding = await ProviderFactory(session, settings).get_embedding(tenant_id, cache=False)
        try:
            job = await session.get(IngestionJob, job_id)
            doc = await session.get(Document, document_id)
            if job is None or doc is None:
                raise _MissingRow()

            job.status = JOB_RUNNING
            job.started_at = datetime.now(UTC)
            job.attempt += 1
            doc.status = DOC_EMBEDDING
            await session.flush()

            try:
                pages = list(
                    (
                        await session.execute(
                            select(DocumentPage)
                            .where(DocumentPage.document_id == document_id)
                            .order_by(DocumentPage.page_no)
                        )
                    )
                    .scalars()
                    .all()
                )
                page_dicts = [
                    {
                        "page_no": p.page_no,
                        "width": p.width,
                        "height": p.height,
                        "blocks": p.blocks,
                        "plain_text": p.plain_text,
                    }
                    for p in pages
                ]

                kb = await session.get(KnowledgeBase, doc.kb_id)
                effective = await resolve_effective_profile(session, doc.kb_id)
                rules = to_ingestion_chunk_rules(effective.chunk_rules)

                drafts = chunk_pages(page_dicts, rules, title=doc.title)
                await session.execute(delete(Chunk).where(Chunk.document_id == document_id))

                texts = [d.content for d in drafts]
                vectors: list[list[float]] = []
                batch_size = settings.embedding_batch_size
                from app.modules.modelops.usage_recorder import (
                    UsageRecorder,
                    estimate_tokens,
                    resolve_usage_route,
                )

                conn_id, provider_type, model = await resolve_usage_route(
                    session, tenant_id, "embedding"
                )
                for i in range(0, len(texts), batch_size):
                    batch = texts[i : i + batch_size]
                    if not batch:
                        continue
                    emb_t0 = time.perf_counter()
                    try:
                        vectors.extend(await embedding.embed(batch, input_type="document"))
                        latency_ms = int((time.perf_counter() - emb_t0) * 1000)
                        await UsageRecorder.record(
                            tenant_id=tenant_id,
                            connection_id=conn_id,
                            kb_id=doc.kb_id,
                            purpose="embedding",
                            provider_type=provider_type,
                            model=model,
                            prompt_tokens=sum(estimate_tokens(t) for t in batch),
                            completion_tokens=0,
                            latency_ms=latency_ms,
                            success=True,
                        )
                    except Exception:
                        latency_ms = int((time.perf_counter() - emb_t0) * 1000)
                        await UsageRecorder.record(
                            tenant_id=tenant_id,
                            connection_id=conn_id,
                            kb_id=doc.kb_id,
                            purpose="embedding",
                            provider_type=provider_type,
                            model=model,
                            prompt_tokens=sum(estimate_tokens(t) for t in batch),
                            completion_tokens=0,
                            latency_ms=latency_ms,
                            success=False,
                            error_code="embed_failed",
                        )
                        raise

                if len(vectors) != len(drafts):
                    raise RuntimeError(
                        f"embedding count mismatch: drafts={len(drafts)} vectors={len(vectors)}"
                    )

                for seq, (draft, vec) in enumerate(zip(drafts, vectors, strict=True)):
                    if len(vec) != settings.embedding_dim:
                        raise RuntimeError(
                            f"embedding dim mismatch: got {len(vec)}, "
                            f"expect {settings.embedding_dim}"
                        )
                    tsv_text = build_tsv(draft.content)
                    tsv_value = (
                        await session.execute(select(func.to_tsvector("simple", tsv_text)))
                    ).scalar_one()
                    session.add(
                        Chunk(
                            id=uuid7(),
                            tenant_id=tenant_id,
                            kb_id=doc.kb_id,
                            document_id=document_id,
                            seq=seq,
                            content=draft.content,
                            raw_content=draft.raw_content,
                            heading_path=draft.heading_path,
                            chunk_type=draft.chunk_type,
                            page_start=draft.page_start,
                            page_end=draft.page_end,
                            bboxes=draft.bboxes,
                            token_count=draft.token_count,
                            embedding=vec,
                            tsv=tsv_value,
                            meta=draft.metadata,
                        )
                    )

                if kb:
                    other = (
                        await session.execute(
                            select(func.count())
                            .select_from(Chunk)
                            .where(Chunk.kb_id == kb.id, Chunk.document_id != document_id)
                        )
                    ).scalar_one()
                    kb.chunk_count = int(other) + len(drafts)

                doc.status = DOC_READY
                doc.error_code = None
                doc.error_detail = None
                job.status = JOB_SUCCEEDED
                job.progress = 1.0
                job.finished_at = datetime.now(UTC)
                await session.flush()
                return "ready"
            except Exception as exc:
                logger.exception("embed_failed", document_id=str(document_id))
                doc.status = DOC_FAILED
                doc.error_code = "embed_failed"
                doc.error_detail = str(exc)[:2000]
                job.status = JOB_FAILED
                job.error_code = "embed_failed"
                job.error_detail = str(exc)[:2000]
                job.finished_at = datetime.now(UTC)
                return "failed"
        finally:
            await aclose_provider(embedding)
