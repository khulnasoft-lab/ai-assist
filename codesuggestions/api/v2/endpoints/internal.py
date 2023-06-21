from time import time
from typing import Optional

import structlog
from dependency_injector.wiring import Provide, inject
from dependency_injector.providers import FactoryAggregate, Factory
from fastapi import APIRouter, Depends
from pydantic import BaseModel, constr

from codesuggestions.api.timing import timing
from codesuggestions.deps import CodeSuggestionsContainer
from codesuggestions.suggestions import CodeSuggestionsUseCaseV2
from codesuggestions.api.rollout import ModelRollout

from starlette.concurrency import run_in_threadpool
from starlette_context import context

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("codesuggestions")

router = APIRouter(
    prefix="/code_completions",
    tags=["completions"],
)


class CurrentFile(BaseModel):
    file_name: constr(strip_whitespace=True, max_length=255)
    content_above_cursor: constr(max_length=100000) = ""
    content_below_cursor: constr(max_length=100000)

class ModelParameters(BaseModel):
    temperature: float = 0.2
    max_decode_steps: int = 16
    top_p: float = 0.95
    top_k: int = 40
    max_decode_steps: int = 16

class CompletionsRequest(BaseModel):
    prompt_version: int = 1
    project_path: Optional[constr(strip_whitespace=True, max_length=255)]
    current_file: CurrentFile
    model: str
    instances: Optional[dict[str, str]] = {}
    parameters: Optional[ModelParameters] = ModelParameters()


class CompletionsResponse(BaseModel):
    class Choice(BaseModel):
        text: str
        index: int = 0
        finish_reason: str = "length"

    class Model(BaseModel):
        engine: str
        name: str

    id: str
    model: Model
    object: str = "text_completion"
    created: int
    choices: list[Choice]


@router.post("", response_model=CompletionsResponse)
@inject
async def completions(
    req: CompletionsRequest,
    engine_factory: FactoryAggregate = Depends(
        Provide[CodeSuggestionsContainer.engine_factory.provider]
    ),
    code_suggestions: Factory[CodeSuggestionsUseCaseV2] = Depends(
        Provide[CodeSuggestionsContainer.usecase_v2.provider]
    ),
):
    usecase = code_suggestions(engine=engine_factory(req.model))

    suggestion = await run_in_threadpool(
        get_suggestions,
        usecase,
        req,
    )

    return CompletionsResponse(
        id="id",
        created=int(time()),
        model=CompletionsResponse.Model(
            engine=context.get("model_engine", ""), name=context.get("model_name", "")
        ),
        choices=[
            CompletionsResponse.Choice(text=suggestion),
        ],
    )


@timing("get_internal_suggestions_duration_s")
def get_suggestions(
    usecase: CodeSuggestionsUseCaseV2,
    req: CompletionsRequest,
):
    return usecase.parameterised_completion(
        req.current_file.content_above_cursor,
        req.current_file.file_name,
        instances=req.instances,
        temperature=req.parameters.temperature,
        top_p=req.parameters.top_p,
        top_k=req.parameters.top_k,
        max_decode_steps=req.parameters.max_decode_steps,
    )
