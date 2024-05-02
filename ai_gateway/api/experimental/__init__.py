from fastapi import APIRouter

from ai_gateway.api.experimental.agents import dynamic_test_cases

__all__ = ["api_router"]

api_router = APIRouter()

api_router.include_router(
    dynamic_test_cases.router, prefix="/dynamic_test_cases", tags=["dynamic_test_cases"]
)
