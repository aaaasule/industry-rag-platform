"""M4：月度 Token 配额 429。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import redis
from httpx import AsyncClient
from sqlalchemy import delete

from app.modules.identity.models import Tenant
from app.modules.ingestion.chunkers.tsv import build_tsv
from app.modules.knowledge.models import Chunk, Document, KnowledgeBase
from app.modules.modelops.usage_models import LlmUsage
from app.platform.config import get_settings
from app.platform.db import session_scope
from app.platform.ids import uuid7
from app.platform.llm.fake import FakeEmbeddingProvider
from tests.conftest import Fixture


def _quota_cache_key(tenant_id: uuid.UUID) -> str:
    month = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m")
    return f"irp:quota:{tenant_id}:{month}"


async def _set_monthly_tokens(tenant_id: uuid.UUID, limit: int) -> None:
    async with session_scope() as session:
        tenant = await session.get(Tenant, tenant_id)
        assert tenant is not None
        q = dict(tenant.quota or {})
        q["monthly_tokens"] = limit
        tenant.quota = q


async def _seed_usage(tenant_id: uuid.UUID, tokens: int) -> uuid.UUID:
    usage_id = uuid7()
    async with session_scope(tenant_id=tenant_id) as session:
        session.add(
            LlmUsage(
                id=usage_id,
                tenant_id=tenant_id,
                purpose="chat",
                provider_type="fake",
                model="fake",
                prompt_tokens=tokens,
                completion_tokens=0,
                latency_ms=1,
                success=True,
                created_at=datetime.now(UTC),
            )
        )
    return usage_id


async def test_search_quota_exceeded_returns_429(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    settings = get_settings()
    r = redis.from_url(settings.redis_url, decode_responses=True)
    r.delete(_quota_cache_key(fixture_data.primary_tenant_id))

    await _set_monthly_tokens(fixture_data.primary_tenant_id, 100)
    usage_id = await _seed_usage(fixture_data.primary_tenant_id, 100)

    emb = FakeEmbeddingProvider(dimension=1024)
    text = "配额测试文档内容"
    vec = (await emb.embed([text], input_type="document"))[0]
    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        from sqlalchemy import func, select

        kb = KnowledgeBase(
            tenant_id=fixture_data.primary_tenant_id,
            name="配额检索库",
            embedding_model="fake",
            embedding_dim=1024,
            created_by=fixture_data.user_id,
        )
        session.add(kb)
        await session.flush()
        doc = Document(
            tenant_id=fixture_data.primary_tenant_id,
            kb_id=kb.id,
            title="doc",
            source_type="upload",
            mime_type="text/plain",
            file_size=10,
            checksum=f"sha256:{uuid.uuid4().hex}",
            storage_key=f"tenants/{fixture_data.primary_tenant_id}/documents/{uuid7()}/o.txt",
            status="ready",
            page_count=1,
            uploaded_by=fixture_data.user_id,
        )
        session.add(doc)
        await session.flush()
        tsv_value = (
            await session.execute(select(func.to_tsvector("simple", build_tsv(text))))
        ).scalar_one()
        session.add(
            Chunk(
                tenant_id=fixture_data.primary_tenant_id,
                kb_id=kb.id,
                document_id=doc.id,
                seq=0,
                content=text,
                raw_content=text,
                heading_path=[],
                chunk_type="text",
                page_start=1,
                page_end=1,
                bboxes=[],
                token_count=10,
                embedding=vec,
                tsv=tsv_value,
            )
        )
        kb_id = kb.id

    resp = await client.post(
        "/api/v1/search",
        headers=auth_headers,
        json={"query": "配额", "kb_ids": [str(kb_id)], "top_k": 3},
    )
    assert resp.status_code == 429, resp.text
    body = resp.json()["error"]
    assert body["code"] == "quota_exceeded"
    assert body["details"]["limit"] == 100
    assert body["details"]["used"] >= 100
    assert "reset_at" in body["details"]
    assert int(resp.headers.get("Retry-After", "0")) > 0

    # 清理
    r.delete(_quota_cache_key(fixture_data.primary_tenant_id))
    await _set_monthly_tokens(fixture_data.primary_tenant_id, 0)
    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        await session.execute(delete(LlmUsage).where(LlmUsage.id == usage_id))


async def test_unlimited_quota_allows_search(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    settings = get_settings()
    r = redis.from_url(settings.redis_url, decode_responses=True)
    r.delete(_quota_cache_key(fixture_data.primary_tenant_id))
    await _set_monthly_tokens(fixture_data.primary_tenant_id, 0)

    resp = await client.post(
        "/api/v1/search",
        headers=auth_headers,
        json={"query": "任意", "kb_ids": [], "top_k": 3},
    )
    # 无 KB 可能 200 空结果或业务错误，但不应是配额 429
    assert resp.status_code != 429, resp.text


async def test_chat_quota_exceeded_returns_429(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    settings = get_settings()
    r = redis.from_url(settings.redis_url, decode_responses=True)
    r.delete(_quota_cache_key(fixture_data.primary_tenant_id))
    await _set_monthly_tokens(fixture_data.primary_tenant_id, 10)
    usage_id = await _seed_usage(fixture_data.primary_tenant_id, 50)

    resp = await client.post(
        "/api/v1/chat/completions",
        headers=auth_headers,
        json={"message": "你好", "kb_ids": []},
    )
    assert resp.status_code == 429, resp.text
    assert resp.json()["error"]["code"] == "quota_exceeded"
    assert int(resp.headers.get("Retry-After", "0")) > 0

    r.delete(_quota_cache_key(fixture_data.primary_tenant_id))
    await _set_monthly_tokens(fixture_data.primary_tenant_id, 0)
    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        await session.execute(delete(LlmUsage).where(LlmUsage.id == usage_id))
