import structlog
from fastapi import APIRouter, Depends, Request

from dependency_injector.providers import Factory
from ai_gateway.api.feature_category import feature_categories
from ai_gateway.async_dependency_resolver import get_chat_litellm_factory_provider
from ai_gateway.auth.request import authorize_with_unit_primitive_header
from ai_gateway.gitlab_features import FEATURE_CATEGORIES_FOR_PROXY_ENDPOINTS
from ai_gateway.models.base import KindModelProvider
from ai_gateway.proxy.clients import VertexAIProxyClient

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("proxy")

router = APIRouter()


@router.post(f"/{KindModelProvider.LITELLM.value}" + "/{path:path}")
@feature_categories(FEATURE_CATEGORIES_FOR_PROXY_ENDPOINTS)
@authorize_with_unit_primitive_header()
async def lite_llm(
    request: Request,
    litellm_factory: Factory = Depends(get_chat_litellm_factory_provider),
):
    model = litellm_factory(
        name=payload.model,
        endpoint=payload.model_endpoint,
        api_key=payload.model_api_key,
    )

    completion = await model.generate(
        messages=payload.content,
        stream=chat_request.stream,
    )
    
    return await litellm_factory.proxy(request)
