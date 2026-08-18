"""M3：chunks 列表与消息反馈。"""

from __future__ import annotations

import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.main import create_app
from app.modules.chat.models import (
    MSG_COMPLETED,
    ROLE_ASSISTANT,
    ROLE_USER,
    Conversation,
    Message,
)
from app.modules.ingestion.chunkers.tsv import build_tsv
from app.modules.knowledge.models import Chunk, Document, DocumentPage, KnowledgeBase
from app.platform.db import session_scope
from app.platform.ids import uuid7
from app.platform.llm.fake import FakeEmbeddingProvider
from tests.conftest import Fixture


async def _seed_doc_with_chunk(fixture: Fixture) -> tuple[uuid.UUID, uuid.UUID]:
    emb = FakeEmbeddingProvider(dimension=1024)
    content = "液压站压力异常时应检查溢流阀。"
    vec = (await emb.embed([content], input_type="document"))[0]
    async with session_scope(
        tenant_id=fixture.primary_tenant_id, user_id=fixture.user_id
    ) as session:
        kb = KnowledgeBase(
            tenant_id=fixture.primary_tenant_id,
            name="M3 测试库",
            embedding_model="fake",
            embedding_dim=1024,
            created_by=fixture.user_id,
        )
        session.add(kb)
        await session.flush()
        doc = Document(
            tenant_id=fixture.primary_tenant_id,
            kb_id=kb.id,
            title="液压手册",
            source_type="upload",
            mime_type="application/pdf",
            file_size=100,
            checksum=f"sha256:{uuid.uuid4().hex}",
            storage_key=f"tenants/{fixture.primary_tenant_id}/documents/{uuid7()}/o.pdf",
            status="ready",
            page_count=2,
            uploaded_by=fixture.user_id,
        )
        session.add(doc)
        await session.flush()
        tsv_value = (
            await session.execute(select(func.to_tsvector("simple", build_tsv(content))))
        ).scalar_one()
        session.add(
            Chunk(
                tenant_id=fixture.primary_tenant_id,
                kb_id=kb.id,
                document_id=doc.id,
                seq=0,
                content=f"《液压手册》\n\n{content}",
                raw_content=content,
                heading_path=["4 故障"],
                chunk_type="text",
                page_start=2,
                page_end=2,
                bboxes=[{"page": 2, "bbox": [72.0, 100.0, 400.0, 140.0]}],
                token_count=12,
                embedding=vec,
                tsv=tsv_value,
            )
        )
        session.add(
            DocumentPage(
                tenant_id=fixture.primary_tenant_id,
                document_id=doc.id,
                page_no=2,
                width=595.0,
                height=842.0,
                blocks=[],
                plain_text=content,
                source="text",
            )
        )
        return kb.id, doc.id


async def test_list_document_chunks(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    _, doc_id = await _seed_doc_with_chunk(fixture_data)
    resp = await client.get(f"/api/v1/documents/{doc_id}/chunks", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["content"] == "液压站压力异常时应检查溢流阀。"
    assert rows[0]["heading_path"] == ["4 故障"]
    assert rows[0]["page_start"] == 2
    assert rows[0]["bboxes"][0]["page"] == 2

    missing = await client.get(
        "/api/v1/documents/00000000-0000-7000-8000-000000000099/chunks",
        headers=auth_headers,
    )
    assert missing.status_code == 404


async def test_list_document_pages(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    _, doc_id = await _seed_doc_with_chunk(fixture_data)
    resp = await client.get(f"/api/v1/documents/{doc_id}/pages", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["page_no"] == 2
    assert "溢流阀" in rows[0]["plain_text"]
    assert rows[0]["source"] == "text"

    missing = await client.get(
        "/api/v1/documents/00000000-0000-7000-8000-000000000099/pages",
        headers=auth_headers,
    )
    assert missing.status_code == 404


async def test_message_feedback_upsert(auth_headers: dict[str, str], fixture_data: Fixture) -> None:
    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        conv = Conversation(
            id=uuid7(),
            tenant_id=fixture_data.primary_tenant_id,
            user_id=fixture_data.user_id,
            kb_ids=[],
            title="反馈测试",
        )
        session.add(conv)
        await session.flush()
        user_msg = Message(
            id=uuid7(),
            tenant_id=fixture_data.primary_tenant_id,
            conversation_id=conv.id,
            role=ROLE_USER,
            content="问题",
            status=MSG_COMPLETED,
        )
        asst = Message(
            id=uuid7(),
            tenant_id=fixture_data.primary_tenant_id,
            conversation_id=conv.id,
            role=ROLE_ASSISTANT,
            content="回答 [1]",
            status=MSG_COMPLETED,
            retrieval_meta={"used_citations": [1]},
        )
        session.add_all([user_msg, asst])
        conv_id = conv.id
        asst_id = asst.id
        user_msg_id = user_msg.id

    app = create_app()
    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http,
        app.router.lifespan_context(app),
    ):
        up = await http.post(
            f"/api/v1/messages/{asst_id}/feedback",
            headers=auth_headers,
            json={"rating": "up"},
        )
        assert up.status_code == 200, up.text
        assert up.json()["rating"] == "up"

        down = await http.post(
            f"/api/v1/messages/{asst_id}/feedback",
            headers=auth_headers,
            json={"rating": "down", "reason": "bad_citation"},
        )
        assert down.status_code == 200, down.text
        assert down.json()["rating"] == "down"
        assert down.json()["reason"] == "bad_citation"

        bad = await http.post(
            f"/api/v1/messages/{user_msg_id}/feedback",
            headers=auth_headers,
            json={"rating": "up"},
        )
        assert bad.status_code == 422

        msgs = await http.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_headers)
        assert msgs.status_code == 200
        asst_out = next(m for m in msgs.json() if m["id"] == str(asst_id))
        assert asst_out["used_citations"] == [1]
        assert asst_out["feedback"]["rating"] == "down"
        assert asst_out["feedback"]["reason"] == "bad_citation"
