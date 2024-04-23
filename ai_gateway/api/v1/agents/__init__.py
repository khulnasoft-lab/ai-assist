from fastapi import APIRouter

from ai_gateway.api.v1.agents import issues

__all__ = [
    "router",
]

router = APIRouter()
router.include_router(issues.router)
