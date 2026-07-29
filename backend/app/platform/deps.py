"""FastAPI 依赖注入。

关键顺序：先解析 token 得到租户，再据此打开数据库会话并写入 RLS 会话变量。
反过来（先开会话再认证）会出现一小段"无租户上下文的已连接事务"，容易被后续
改动利用成越权入口。
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.config import Settings, get_settings
from app.platform.db import get_sessionmaker, set_rls_context
from app.platform.errors import Forbidden, Unauthenticated
from app.platform.llm.base import EmbeddingProvider, LLMProvider, RerankProvider
from app.platform.logging import tenant_id_var, user_id_var
from app.platform.security import TokenClaims, decode_token

_bearer = HTTPBearer(auto_error=False)


def settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dep)]


async def current_claims(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> TokenClaims:
    if credentials is None:
        raise Unauthenticated()
    claims = decode_token(credentials.credentials, expected_type="access")
    tenant_id_var.set(str(claims.tenant_id))
    user_id_var.set(str(claims.user_id))
    return claims


ClaimsDep = Annotated[TokenClaims, Depends(current_claims)]


async def get_session() -> AsyncIterator[AsyncSession]:
    """无租户上下文的会话。仅用于登录、刷新等尚未确定租户的场景。"""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_tenant_session(claims: ClaimsDep) -> AsyncIterator[AsyncSession]:
    """带租户上下文的会话，业务接口一律用这个。"""
    async with get_sessionmaker()() as session:
        await set_rls_context(session, tenant_id=claims.tenant_id, user_id=claims.user_id)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


TenantSessionDep = Annotated[AsyncSession, Depends(get_tenant_session)]


def require_role(minimum: str) -> Callable[[TokenClaims], Awaitable[TokenClaims]]:
    """角色门禁。用法：dependencies=[Depends(require_role(ROLE_ADMIN))]"""
    from app.modules.identity.models import role_at_least

    async def _guard(claims: ClaimsDep) -> TokenClaims:
        if not role_at_least(claims.role, minimum):
            raise Forbidden(f"该操作需要 {minimum} 及以上角色")
        return claims

    return _guard


def current_tenant_id(claims: ClaimsDep) -> uuid.UUID:
    return claims.tenant_id


TenantIdDep = Annotated[uuid.UUID, Depends(current_tenant_id)]


def llm_provider(request: Request) -> LLMProvider:
    return request.app.state.llm


def embedding_provider(request: Request) -> EmbeddingProvider:
    return request.app.state.embedding


def rerank_provider(request: Request) -> RerankProvider:
    return request.app.state.rerank


async def resolved_llm(claims: ClaimsDep, session: TenantSessionDep) -> LLMProvider:
    from app.modules.modelops.provider_factory import ProviderFactory

    return await ProviderFactory(session).get_llm(claims.tenant_id)


async def resolved_embedding(claims: ClaimsDep, session: TenantSessionDep) -> EmbeddingProvider:
    from app.modules.modelops.provider_factory import ProviderFactory

    return await ProviderFactory(session).get_embedding(claims.tenant_id)


async def resolved_rerank(claims: ClaimsDep, session: TenantSessionDep) -> RerankProvider:
    from app.modules.modelops.provider_factory import ProviderFactory

    return await ProviderFactory(session).get_rerank(claims.tenant_id)


LLMDep = Annotated[LLMProvider, Depends(llm_provider)]
EmbeddingDep = Annotated[EmbeddingProvider, Depends(embedding_provider)]
RerankDep = Annotated[RerankProvider, Depends(rerank_provider)]

ResolvedLLMDep = Annotated[LLMProvider, Depends(resolved_llm)]
ResolvedEmbeddingDep = Annotated[EmbeddingProvider, Depends(resolved_embedding)]
ResolvedRerankDep = Annotated[RerankProvider, Depends(resolved_rerank)]
