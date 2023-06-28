from fastapi import APIRouter

from codesuggestions.api.v2.endpoints import internal, suggestions
from codesuggestions.api.v2.experimental import code


api_router = APIRouter()

api_router.include_router(suggestions.router, prefix="/v2")
api_router.include_router(code.router, prefix="/experimental")
api_router.include_router(internal.router, prefix="/internal/v2")
