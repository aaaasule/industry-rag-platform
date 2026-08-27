"""接入点管理业务逻辑。"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.modules.audit.service import AuditService
from app.modules.modelops.credentials import (
    credential_hint,
    encrypt_credential,
    mask_credential,
)
from app.modules.modelops.models import (
    HEALTH_DOWN,
    HEALTH_HEALTHY,
    HEALTH_UNKNOWN,
    PROVIDER_FAKE,
    PURPOSES,
    ModelConnection,
)
from app.modules.modelops.probe import probe_connection
from app.modules.modelops.provider_factory import ProviderFactory, clear_provider_cache
from app.modules.modelops.repository import ModelConnectionRepository
from app.modules.modelops.schemas import (
    ConnectionTestResult,
    CredentialUpdate,
    ModelConnectionCreate,
    ModelConnectionOut,
    ModelConnectionUpdate,
    RoutesOut,
)
from app.platform.config import Settings, get_settings
from app.platform.errors import AppError, Forbidden, NotFound
from app.platform.ids import uuid7
from app.platform.security import TokenClaims


class ModelOpsService:
    def __init__(
        self,
        repo: ModelConnectionRepository,
        settings: Settings | None = None,
    ) -> None:
        self._repo = repo
        self._settings = settings or get_settings()
        self._audit = AuditService(repo._session)

    async def list_connections(self, claims: TokenClaims) -> list[ModelConnectionOut]:
        rows = await self._repo.list_visible(claims.tenant_id)
        return [_out(r) for r in rows]

    async def create(
        self, claims: TokenClaims, payload: ModelConnectionCreate
    ) -> ModelConnectionOut:
        self._validate_purposes(payload.purposes)
        api_key = payload.api_key or ""
        if payload.provider_type != PROVIDER_FAKE and not api_key:
            raise AppError("openai_compatible 接入点必须提供 api_key", code="validation_error")

        row = ModelConnection(
            id=uuid7(),
            tenant_id=claims.tenant_id,
            name=payload.name,
            provider_type=payload.provider_type,
            base_url=payload.base_url,
            credential_cipher=encrypt_credential(api_key, self._settings),
            credential_hint=credential_hint(api_key),
            model=payload.model,
            purposes=list(payload.purposes),
            priority=payload.priority,
            enabled=payload.enabled,
            health=HEALTH_UNKNOWN,
            extra=payload.extra,
            version=1,
        )
        await self._repo.add(row)
        await self._repo._session.refresh(row)
        out = _out(row)
        await self._audit.record(
            tenant_id=claims.tenant_id,
            actor_id=claims.user_id,
            action="model_connection.create",
            target_type="model_connection",
            target_id=row.id,
            payload={"name": out.name, "purposes": out.purposes, "model": out.model},
        )
        return out

    async def update(
        self,
        claims: TokenClaims,
        connection_id: uuid.UUID,
        payload: ModelConnectionUpdate,
    ) -> ModelConnectionOut:
        row = await self._require_tenant_row(claims, connection_id)
        data = payload.model_dump(exclude_unset=True)
        if "purposes" in data and data["purposes"] is not None:
            self._validate_purposes(data["purposes"])
            row.purposes = list(data["purposes"])
        for field in ("name", "base_url", "model", "priority", "enabled", "extra"):
            if field in data and data[field] is not None:
                setattr(row, field, data[field])
        row.version += 1
        await self._repo._session.flush()
        await self._repo._session.refresh(row)
        out = _out(row)
        clear_provider_cache()
        await self._audit.record(
            tenant_id=claims.tenant_id,
            actor_id=claims.user_id,
            action="model_connection.update",
            target_type="model_connection",
            target_id=row.id,
            payload={"version": out.version, "fields": sorted(data.keys())},
        )
        return out

    async def update_credential(
        self,
        claims: TokenClaims,
        connection_id: uuid.UUID,
        payload: CredentialUpdate,
    ) -> ModelConnectionOut:
        row = await self._require_tenant_row(claims, connection_id)
        row.credential_cipher = encrypt_credential(payload.api_key, self._settings)
        row.credential_hint = credential_hint(payload.api_key)
        row.version += 1
        await self._repo._session.flush()
        await self._repo._session.refresh(row)
        out = _out(row)
        clear_provider_cache()
        await self._audit.record(
            tenant_id=claims.tenant_id,
            actor_id=claims.user_id,
            action="model_connection.credential_update",
            target_type="model_connection",
            target_id=row.id,
            payload={"version": out.version},
        )
        return out

    async def delete(self, claims: TokenClaims, connection_id: uuid.UUID) -> None:
        row = await self._require_tenant_row(claims, connection_id)
        name = row.name
        await self._repo.delete(row)
        clear_provider_cache()
        await self._audit.record(
            tenant_id=claims.tenant_id,
            actor_id=claims.user_id,
            action="model_connection.delete",
            target_type="model_connection",
            target_id=connection_id,
            payload={"name": name},
        )

    async def test(self, claims: TokenClaims, connection_id: uuid.UUID) -> ConnectionTestResult:
        row = await self._repo.get(connection_id)
        if row is None:
            raise NotFound("接入点不存在")
        if row.tenant_id is not None and row.tenant_id != claims.tenant_id:
            raise NotFound("接入点不存在")

        result = await probe_connection(row, settings=self._settings)
        # 平台行 RLS WITH CHECK 禁止应用角色写入；health 由定时 probe 任务（迁移角色）更新
        persist_health = row.tenant_id is not None
        if result.ok:
            if persist_health:
                row.health = HEALTH_HEALTHY
                row.health_checked_at = datetime.now(UTC)
                await self._repo._session.flush()
            await self._audit.record(
                tenant_id=claims.tenant_id,
                actor_id=claims.user_id,
                action="model_connection.test",
                target_type="model_connection",
                target_id=row.id,
                payload={"ok": True, "latency_ms": round(result.latency_ms, 2)},
            )
            return ConnectionTestResult(
                ok=True, latency_ms=round(result.latency_ms, 2), model_echo=row.model
            )

        if persist_health:
            row.health = HEALTH_DOWN
            row.health_checked_at = datetime.now(UTC)
            await self._repo._session.flush()
        await self._audit.record(
            tenant_id=claims.tenant_id,
            actor_id=claims.user_id,
            action="model_connection.test",
            target_type="model_connection",
            target_id=row.id,
            payload={"ok": False, "error": result.error_message},
        )
        return ConnectionTestResult(
            ok=False,
            latency_ms=round(result.latency_ms, 2),
            error_code="network_error",
            error_message=result.error_message,
        )

    async def routes(self, claims: TokenClaims) -> RoutesOut:
        return await ProviderFactory(self._repo._session, self._settings).routes(claims.tenant_id)

    async def _require_tenant_row(
        self, claims: TokenClaims, connection_id: uuid.UUID
    ) -> ModelConnection:
        row = await self._repo.get(connection_id)
        if row is None:
            raise NotFound("接入点不存在")
        if row.tenant_id is None:
            raise Forbidden("不能修改平台级接入点")
        if row.tenant_id != claims.tenant_id:
            raise NotFound("接入点不存在")
        return row

    @staticmethod
    def _validate_purposes(purposes: Sequence[str]) -> None:
        bad = [p for p in purposes if p not in PURPOSES]
        if bad:
            raise AppError(f"无效用途: {bad}", code="validation_error")


def _out(row: ModelConnection) -> ModelConnectionOut:
    return ModelConnectionOut(
        id=row.id,
        tenant_id=row.tenant_id,
        scope="platform" if row.tenant_id is None else "tenant",
        name=row.name,
        provider_type=row.provider_type,
        base_url=row.base_url,
        model=row.model,
        purposes=list(row.purposes or []),
        priority=row.priority,
        enabled=row.enabled,
        health=row.health,
        health_checked_at=row.health_checked_at,
        credential_masked=mask_credential(row.credential_hint),
        version=row.version,
        extra=dict(row.extra or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
