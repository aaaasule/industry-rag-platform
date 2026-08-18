"""SSE 问答冒烟测试。"""

from __future__ import annotations

import json
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


def _event_data(events: list[tuple[str, str]], name: str) -> dict:
    for event, payload in events:
        if event == name:
            return json.loads(payload)
    raise AssertionError(f"missing SSE event {name}")


async def _seed_chat_kb(fixture_data: Fixture) -> uuid.UUID:
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
        return kb.id


async def test_chat_completions_sse_done_or_no_answer(
    auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    kb_id = await _seed_chat_kb(fixture_data)
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


async def test_regenerate_reuses_message_and_rejects_non_last(
    auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    kb_id = await _seed_chat_kb(fixture_data)
    app = create_app()
    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http,
        app.router.lifespan_context(app),
    ):
        first = await http.post(
            "/api/v1/chat/completions",
            headers=auth_headers,
            json={"kb_ids": [str(kb_id)], "message": "HYD-2201 保养周期是多久？"},
        )
        assert first.status_code == 200, first.text
        created = _event_data(_parse_sse(first.text), "message_created")
        conv_id = created["conversation_id"]
        asst_id = created["message_id"]

        regen = await http.post(
            f"/api/v1/messages/{asst_id}/regenerate",
            headers=auth_headers,
        )
        assert regen.status_code == 200, regen.text
        regen_events = _parse_sse(regen.text)
        regen_names = [e[0] for e in regen_events]
        assert "message_created" in regen_names
        assert "retrieval" in regen_names
        assert "done" in regen_names or "no_answer" in regen_names
        assert _event_data(regen_events, "message_created")["message_id"] == asst_id

        hist = await http.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_headers)
        assert hist.status_code == 200, hist.text
        rows = hist.json()
        assert len(rows) == 2
        assert rows[0]["role"] == "user"
        assert rows[1]["id"] == asst_id
        assert rows[1]["role"] == "assistant"

        user_id = rows[0]["id"]
        bad_user = await http.post(f"/api/v1/messages/{user_id}/regenerate", headers=auth_headers)
        assert bad_user.status_code == 422

        second = await http.post(
            "/api/v1/chat/completions",
            headers=auth_headers,
            json={"conversation_id": conv_id, "message": "再问一次保养周期"},
        )
        assert second.status_code == 200, second.text
        stale = await http.post(f"/api/v1/messages/{asst_id}/regenerate", headers=auth_headers)
        assert stale.status_code == 422
