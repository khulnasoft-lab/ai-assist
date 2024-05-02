from fastapi import APIRouter
from fastapi.responses import JSONResponse

__all__ = [
    "router",
]

router = APIRouter(
    prefix="",
    tags=["oidc"],
)


@router.get("/.well-known/openid-configuration")
async def provider():
    return JSONResponse({'test': True}, status_code=200)


@router.get("/oauth/discovery/keys")
async def keys():
    return JSONResponse({'test': False}, status_code=200)
