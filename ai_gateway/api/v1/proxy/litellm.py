from time import time
from typing import AsyncIterator, Union

import structlog
from dependency_injector.providers import Factory, FactoryAggregate
from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.authentication import requires

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v1.proxy.typing import LiteLlmRequest
from ai_gateway.async_dependency_resolver import get_litellm_factory_provider
from ai_gateway.models.litellm import LiteLlmChatModel
from ai_gateway.tracking import log_exception

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("proxy")

router = APIRouter()

# - `name` must be registred in unit primitives defined in Customer Dot. `scopes` claim of JWT must include one of the names.
# - `X-Gitlab-Feature-Usage` HTTP header must match one of the following names.
# See https://docs.gitlab.com/ee/architecture/blueprints/ai_gateway/decisions/002_proxy.html for more information.
FEATURES = [
    {"name": "explain_vulnerability", "category": "duo_chat"},
    {"name": "resolve_vulnerability", "category": "duo_chat"},
    {"name": "generate_description", "category": "duo_chat"},
    {"name": "summarize_all_open_notes", "category": "duo_chat"},
    {"name": "summarize_submitted_review", "category": "duo_chat"},
    {"name": "generate_commit_message", "category": "duo_chat"},
    {"name": "summarize_review", "category": "duo_chat"},
    {"name": "fill_in_merge_request_template", "category": "duo_chat"},
    {"name": "analyze_ci_job_failure", "category": "duo_chat"},
]

feature_names = [feature["name"] for feature in FEATURES]


@router.post("/chat/completions")
@requires(feature_names)
@feature_category(FEATURES)
async def chat(
    request: Request,
    litellm_request: LiteLlmRequest,
    litellm_factory: Factory[LiteLlmChatModel] = Depends(get_litellm_factory_provider),
):
    litellm_model = litellm_factory(name=litellm_request.model)

    # return litellm_model.generate(**litellm_request.dict())
    return await litellm_model.generate(messages=litellm_request.messages)
