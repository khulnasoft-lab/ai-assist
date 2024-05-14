import structlog
from fastapi import APIRouter, Depends, Request
from starlette.authentication import requires

from ai_gateway.agents.registry import LocalAgentRegistry
from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v1.x_ray.typing import (
    PackageFilePromptPayload,
    XRayRequest,
    XRayResponse,
)
from ai_gateway.async_dependency_resolver import get_x_ray_anthropic_claude
from ai_gateway.models import AnthropicModel

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("x-ray")

router = APIRouter()


@router.post("/libraries", response_model=XRayResponse)
@requires("code_suggestions")
@feature_category("code_suggestions")
async def libraries(
    request: Request,
    x_ray_request: XRayRequest,
    model: AnthropicModel = Depends(get_x_ray_anthropic_claude),
):
    payload = x_ray_request.prompt_components[0].payload

    if isinstance(payload, PackageFilePromptPayload):
        prompt = payload.prompt
    else:
        libs = payload.libraries
        separator = "---"
        registry = LocalAgentRegistry(model.client)
        agent = registry.get("x_ray", "libraries")
        prompt = agent.prompt(
            key="describe",
            separator=separator,
            type_description=payload.type_description,
            libs=libs,
        )

    completion = await model.generate(
        prefix=prompt,
        _suffix="",
    )

    return XRayResponse(response=completion.text)
