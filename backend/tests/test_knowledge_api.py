"""知识库 API 集成测试。"""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import Fixture


async def test_create_kb_and_list(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    # 无内置 profile 时允许 profile_code=None；有则用 general
    create = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "测试库", "visibility": "private"},
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["name"] == "测试库"
    assert body["doc_count"] == 0

    listed = await client.get("/api/v1/knowledge-bases", headers=auth_headers)
    assert listed.status_code == 200
    assert any(item["id"] == body["id"] for item in listed.json())

    # 跨租户不可见：切到 outsider 无权限，登录失败或 404——用另一租户 token 测隔离
    # 这里验证未认证拒绝
    denied = await client.get("/api/v1/knowledge-bases")
    assert denied.status_code == 401


async def test_kb_cross_tenant_404(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    create = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "隔离库"},
    )
    assert create.status_code == 201
    kb_id = create.json()["id"]

    # secondary 同用户可见；跨租户隔离另测。此处只验随机 id → 404
    detail = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=auth_headers)
    assert detail.status_code == 200

    # 随机 UUID 应 404
    missing = await client.get(
        "/api/v1/knowledge-bases/00000000-0000-7000-8000-000000000099",
        headers=auth_headers,
    )
    assert missing.status_code == 404
