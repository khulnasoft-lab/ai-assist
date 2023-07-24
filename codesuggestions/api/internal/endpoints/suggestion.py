from time import time
from enum import Enum
from typing import Optional

import structlog
from dependency_injector.wiring import Provide, inject
from dependency_injector.providers import FactoryAggregate, Factory
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, constr, conlist

from codesuggestions.deps import CodeSuggestionsContainer
from codesuggestions.suggestions import CodeSuggestions
from codesuggestions.api.rollout import ModelRolloutBasePlan
from codesuggestions.instrumentators.base import Telemetry, TelemetryInstrumentator

from starlette_context import context

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("codesuggestions")

router = APIRouter(
    prefix="/code-suggestions",
    tags=["code-suggestions"],
)



class PromptType(str, Enum):
    PROMPT = "prompt"
    EDITOR_CONTENT = "editor_content"


class RequestMetadata(BaseModel):
    source: str
    version: str


class PromptPayload(BaseModel):
    filename: str
    project_id: str
    project_path: str
    before_cursor: str
    after_cursor: str



class PromptComponent(BaseModel):
    type: PromptType
    metadata: RequestMetadata
    payload: PromptPayload


class SuggestionsRequest(BaseModel):
    prompt_components: list[PromptComponent]
    telemetry: conlist(Telemetry, max_items=10) = []


class ResponseMetadata(BaseModel):
    identifier: str
    model: str
    timestamp: int

class SuggestionsResponse(BaseModel):
    response: str
    metadata: ResponseMetadata


@router.post("/completions", response_model=SuggestionsResponse)
@inject
async def completions(
    req: Request,
    payload: SuggestionsRequest,
    # model_rollout_plan: ModelRolloutBasePlan = Depends(
    #     Provide[CodeSuggestionsContainer.model_rollout_plan]
    # ),
    # engine_factory: FactoryAggregate = Depends(
    #     Provide[CodeSuggestionsContainer.engine_factory.provider]
    # ),
    # code_suggestions: Factory[CodeSuggestions] = Depends(
    #     Provide[CodeSuggestionsContainer.code_suggestions.provider]
    # ),
):
    # model_name = model_rollout_plan.route(req.user, payload.project_id)
    # usecase = code_suggestions(engine=engine_factory(model_name))

    with TelemetryInstrumentator().watch(payload.telemetry):
        suggestion = "suggestion response"

    return SuggestionsResponse(
        response=suggestion,
        metadata=ResponseMetadata(
            identifier="deadbeef",
            model="none",
            timestamp=round(time.time() * 1000)
    )
