from fastapi import APIRouter

from ai_gateway.api.v3 import code, user_jwt

__all__ = ["api_router"]

api_router = APIRouter()

api_router.include_router(code.router, prefix="/code", tags=["completions"])
api_router.include_router(user_jwt.router, prefix="/user_jwt", tags=["user_jwt"])
