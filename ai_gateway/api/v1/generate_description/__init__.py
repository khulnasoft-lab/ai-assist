from fastapi import APIRouter

from ai_gateway.api.v1.generate_description import base

__all__ = [
    "router",
]


router = APIRouter()
router.include_router(base.router)
