from fastapi import APIRouter

from ai_gateway.api.v1 import chains, chat, code, proxy, search, x_ray

__all__ = ["api_router"]

api_router = APIRouter()

api_router.include_router(chains.router, prefix="/chains", tags=["chains"])
api_router.include_router(code.router, prefix="/code", tags=["completions"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(x_ray.router, prefix="/x-ray", tags=["x-ray"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(proxy.router, prefix="/proxy", tags=["proxy"])
