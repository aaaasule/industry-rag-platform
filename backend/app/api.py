"""路由汇总。新增业务模块时只在这里挂载，main.py 保持稳定。"""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.chat.router import router as chat_router
from app.modules.identity.memberships_router import router as memberships_router
from app.modules.identity.router import router as identity_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.modelops.router import router as modelops_router
from app.modules.modelops.usage_router import router as usages_router
from app.modules.retrieval.router import router as retrieval_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(identity_router)
api_router.include_router(memberships_router)
api_router.include_router(knowledge_router)
api_router.include_router(retrieval_router)
api_router.include_router(chat_router)
api_router.include_router(audit_router)
api_router.include_router(modelops_router)
api_router.include_router(usages_router)
