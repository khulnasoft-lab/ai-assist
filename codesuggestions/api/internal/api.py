from fastapi import APIRouter

from codesuggestions.api.internal.endpoints import suggestion

api_router = APIRouter()
api_router.prefix = "/internal"

api_router.include_router(suggestion.router)
