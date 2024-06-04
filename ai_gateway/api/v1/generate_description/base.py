from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request, status
from starlette.authentication import requires

from ai_gateway.agents.generate_description import (
    GenerateDescriptionInputs,
    GenerateDescriptionOutput,
)
from ai_gateway.agents.registry import BaseAgentRegistry
from ai_gateway.api.feature_category import feature_category
from ai_gateway.async_dependency_resolver import get_agent_registry
from ai_gateway.gitlab_features import GitLabFeatureCategory, GitLabUnitPrimitive

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("ai")

router = APIRouter()


@router.post(
    "/generate_description",
    response_model=GenerateDescriptionOutput,
    status_code=status.HTTP_200_OK,
)
@requires(GitLabUnitPrimitive.GENERATE_ISSUE_DESCRIPTION)
@feature_category(GitLabFeatureCategory.AI_ABSTRACTION_LAYER)
async def generate_description(
    request: Request,
    inputs: GenerateDescriptionInputs,
    agent_registry: Annotated[BaseAgentRegistry, Depends(get_agent_registry)],
):
    agent = agent_registry.get(
        "generate_description", "base", {"template": inputs.template}
    )

    return await agent.ainvoke(inputs)
