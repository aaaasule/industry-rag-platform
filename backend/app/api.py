"""路由汇总。新增业务模块时只在这里挂载，main.py 保持稳定。"""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.identity.router import router as identity_router
from app.modules.knowledge.router import router as knowledge_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(identity_router)
api_router.include_router(knowledge_router)
