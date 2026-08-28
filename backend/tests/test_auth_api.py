"""认证接口集成测试（打真实数据库）。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from tests.conftest import Fixture


class TestLogin:
    async def test_success_returns_token_pair(
        self, client: AsyncClient, fixture_data: Fixture
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": fixture_data.email, "password": fixture_data.password},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "Bearer"
        assert body["access_token"] and body["refresh_token"]

    async def test_email_is_case_insensitive(
        self, client: AsyncClient, fixture_data: Fixture
    ) -> None:
        # citext 保证的行为，回归测试盯住它
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": fixture_data.email.upper(), "password": fixture_data.password},
        )
        assert resp.status_code == 200

    async def test_wrong_password_and_unknown_user_are_indistinguishable(
        self, client: AsyncClient, fixture_data: Fixture
    ) -> None:
        wrong = await client.post(
            "/api/v1/auth/login",
            json={"email": fixture_data.email, "password": "Definitely-Wrong-1"},
        )
        unknown = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "Definitely-Wrong-1"},
        )
        assert wrong.status_code == unknown.status_code == 401

        # 除 request_id 外响应体必须完全一致，否则可以据此枚举有效账号
        def _comparable(resp_json: dict) -> dict:
            error = dict(resp_json["error"])
            error.pop("request_id", None)
            return error

        assert _comparable(wrong.json()) == _comparable(unknown.json())

    async def test_tenant_slug_selects_target_tenant(
        self, client: AsyncClient, fixture_data: Fixture
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": fixture_data.email,
                "password": fixture_data.password,
                "tenant_slug": fixture_data.secondary_tenant_slug,
            },
        )
        assert resp.status_code == 200
        me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {resp.json()['access_token']}"},
        )
        assert me.json()["current_tenant"]["slug"] == fixture_data.secondary_tenant_slug

    async def test_unjoined_tenant_is_rejected(
        self, client: AsyncClient, fixture_data: Fixture
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": fixture_data.email,
                "password": fixture_data.password,
                "tenant_slug": "some-tenant-i-do-not-belong-to",
            },
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "forbidden"

    async def test_short_password_fails_validation(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/login", json={"email": "a@b.example", "password": "short"}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "validation_error"


class TestSession:
    async def test_me_lists_all_joined_tenants(
        self, client: AsyncClient, fixture_data: Fixture, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["email"] == fixture_data.email
        slugs = {t["slug"] for t in body["tenants"]}
        assert slugs == {fixture_data.primary_tenant_slug, fixture_data.secondary_tenant_slug}

    async def test_me_requires_token(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "unauthenticated"

    async def test_garbage_token_rejected(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401

    async def test_response_carries_request_id(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/auth/me", headers={"X-Request-Id": "trace-me"})
        assert resp.headers["X-Request-Id"] == "trace-me"
        assert resp.json()["error"]["request_id"] == "trace-me"


class TestRefresh:
    async def test_returns_new_pair(self, client: AsyncClient, fixture_data: Fixture) -> None:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": fixture_data.email, "password": fixture_data.password},
        )
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": login.json()["refresh_token"]}
        )
        assert resp.status_code == 200
        assert resp.json()["access_token"]

    async def test_access_token_cannot_be_used_to_refresh(
        self, client: AsyncClient, fixture_data: Fixture
    ) -> None:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": fixture_data.email, "password": fixture_data.password},
        )
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": login.json()["access_token"]}
        )
        assert resp.status_code == 401


class TestSwitchTenant:
    async def test_switches_to_another_joined_tenant(
        self, client: AsyncClient, fixture_data: Fixture, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/switch-tenant",
            json={"tenant_id": str(fixture_data.secondary_tenant_id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {resp.json()['access_token']}"},
        )
        current = me.json()["current_tenant"]
        assert current["id"] == str(fixture_data.secondary_tenant_id)
        # 角色随租户变化，不能沿用切换前的角色
        assert current["role"] == "member"

    async def test_cannot_switch_to_unjoined_tenant(
        self, client: AsyncClient, fixture_data: Fixture, auth_headers: dict[str, str]
    ) -> None:
        # 越权入口：客户端指定 tenant_id，服务端必须校验成员关系
        resp = await client.post(
            "/api/v1/auth/switch-tenant",
            json={"tenant_id": str(fixture_data.outsider_tenant_id)},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    async def test_cannot_switch_to_nonexistent_tenant(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/switch-tenant",
            json={"tenant_id": str(uuid.uuid4())},
            headers=auth_headers,
        )
        assert resp.status_code == 403


class TestProfile:
    async def test_update_display_name(
        self, client: AsyncClient, fixture_data: Fixture, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.patch(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"display_name": "  新显示名  "},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["user"]["display_name"] == "新显示名"

        me = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert me.json()["user"]["display_name"] == "新显示名"

    async def test_change_password_and_login(
        self, client: AsyncClient, fixture_data: Fixture, auth_headers: dict[str, str]
    ) -> None:
        new_password = f"{fixture_data.password}X"
        bad = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={"current_password": "Definitely-Wrong-1", "new_password": new_password},
        )
        assert bad.status_code == 401

        same = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": fixture_data.password,
                "new_password": fixture_data.password,
            },
        )
        assert same.status_code == 422

        ok = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": fixture_data.password,
                "new_password": new_password,
            },
        )
        assert ok.status_code == 204, ok.text

        old_login = await client.post(
            "/api/v1/auth/login",
            json={"email": fixture_data.email, "password": fixture_data.password},
        )
        assert old_login.status_code == 401

        new_login = await client.post(
            "/api/v1/auth/login",
            json={"email": fixture_data.email, "password": new_password},
        )
        assert new_login.status_code == 200

        # 恢复夹具口令，避免影响同会话后续用例
        restore = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {new_login.json()['access_token']}"},
            json={"current_password": new_password, "new_password": fixture_data.password},
        )
        assert restore.status_code == 204


class TestSystem:
    async def test_healthz(self, client: AsyncClient) -> None:
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_readyz_checks_dependencies(self, client: AsyncClient) -> None:
        resp = await client.get("/readyz")
        assert resp.status_code == 200, resp.text
        assert resp.json()["checks"] == {"database": "ok", "redis": "ok"}
