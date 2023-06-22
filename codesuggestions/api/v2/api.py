from fastapi import APIRouter

from codesuggestions.api.v2.endpoints import internal, suggestions


public_api_router = APIRouter()
public_api_router.prefix = "/v2"
public_api_router.include_router(suggestions.router)


internal_api_router = APIRouter()
internal_api_router.prefix = "/internal/v2"
internal_api_router.include_router(internal.router)

api_router = APIRouter()
api_router.include_router(public_api_router)
api_router.include_router(internal_api_router)
