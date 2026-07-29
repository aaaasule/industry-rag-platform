"""SSE 问答冒烟测试。"""

from __future__ import annotations

import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.main import create_app
from app.modules.ingestion.chunkers.tsv import build_tsv
from app.modules.knowledge.models import Chunk, Document, KnowledgeBase
from app.platform.db import session_scope
from app.platform.ids import uuid7
from app.platform.llm.fake import FakeEmbeddingProvider
from tests.conftest import Fixture


def _parse_sse(raw: str) -> list[tuple[str, str]]:
    events: list[tuple[str, str]] = []
    blocks = raw.replace("\r\n", "\n").split("\n\n")
    for block in blocks:
        if not block.strip():
            continue
        event = "message"
        data_lines: list[str] = []
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
        events.append((event, "\n".join(data_lines)))
    return events


async def test_chat_completions_sse_done_or_no_answer(
    auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    emb = FakeEmbeddingProvider(dimension=1024)
    content = "液压泵 HYD-2201 的保养周期为三个月一次。"
    vec = (await emb.embed([content], input_type="document"))[0]

    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        kb = KnowledgeBase(
            tenant_id=fixture_data.primary_tenant_id,
            name="问答测试库",
            embedding_model="fake",
            embedding_dim=1024,
            created_by=fixture_data.user_id,
        )
        session.add(kb)
        await session.flush()
        doc = Document(
            tenant_id=fixture_data.primary_tenant_id,
            kb_id=kb.id,
            title="保养手册",
            source_type="upload",
            mime_type="text/plain",
            file_size=50,
            checksum=f"sha256:{uuid.uuid4().hex}",
            storage_key=f"tenants/{fixture_data.primary_tenant_id}/documents/{uuid7()}/o.txt",
            status="ready",
            page_count=1,
            uploaded_by=fixture_data.user_id,
        )
        session.add(doc)
        await session.flush()
        tsv_value = (
            await session.execute(select(func.to_tsvector("simple", build_tsv(content))))
        ).scalar_one()
        session.add(
            Chunk(
                tenant_id=fixture_data.primary_tenant_id,
                kb_id=kb.id,
                document_id=doc.id,
                seq=0,
                content=content,
                raw_content=content,
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

    app = create_app()
    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http,
        app.router.lifespan_context(app),
    ):
        resp = await http.post(
            "/api/v1/chat/completions",
            headers=auth_headers,
            json={"kb_ids": [str(kb_id)], "message": "HYD-2201 保养周期是多久？"},
        )
        assert resp.status_code == 200, resp.text
        events = _parse_sse(resp.text)
        names = [e[0] for e in events]
        assert "message_created" in names
        assert "retrieval" in names
        assert "done" in names or "no_answer" in names
        if "done" in names:
            assert "citations" in names
            assert "delta" in names
