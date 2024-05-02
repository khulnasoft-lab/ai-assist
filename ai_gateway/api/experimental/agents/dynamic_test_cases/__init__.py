from fastapi import APIRouter

from ai_gateway.api.experimental.agents.dynamic_test_cases import generate

__all__ = [
    "router",
]

router = APIRouter()

router.include_router(generate.router)
