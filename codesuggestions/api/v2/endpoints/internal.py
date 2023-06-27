from time import time
from typing import Optional

import structlog
from dependency_injector.wiring import Provide, inject
from dependency_injector.providers import FactoryAggregate, Factory
from fastapi import APIRouter, Depends
from pydantic import BaseModel, constr, conlist

from codesuggestions.api.timing import timing
from codesuggestions.deps import CodeSuggestionsContainer
from codesuggestions.suggestions import CodeSuggestionsUseCaseV2
from codesuggestions.instrumentators.base import Telemetry, TelemetryInstrumentator


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
    content_above_cursor: constr(max_length=100000)
    content_below_cursor: constr(max_length=100000)


class SuggestionsRequest(BaseModel):
    prompt_version: int = 1
    project_path: Optional[constr(strip_whitespace=True, max_length=255)]
    project_id: Optional[int]
    current_file: CurrentFile
    telemetry: conlist(Telemetry, max_items=10) = []
    provider: str
    related_contents: str


class SuggestionsResponse(BaseModel):
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


@router.post("", response_model=SuggestionsResponse)
@inject
async def completions(
    req: SuggestionsRequest,
    engine_factory: FactoryAggregate = Depends(
        Provide[CodeSuggestionsContainer.engine_factory.provider]
    ),
    code_suggestions: Factory[CodeSuggestionsUseCaseV2] = Depends(
        Provide[CodeSuggestionsContainer.usecase_v2.provider]
    ),
):
    usecase = code_suggestions(engine=engine_factory(req.provider))

    with TelemetryInstrumentator().watch(req.telemetry):
        suggestion = await run_in_threadpool(
            get_suggestions,
            usecase,
            req,
        )

    suggestion = await run_in_threadpool(
        get_suggestions,
        usecase,
        req,
    )

    return SuggestionsResponse(
        id="id",
        created=int(time()),
        model=SuggestionsResponse.Model(
            engine=context.get("model_engine", ""), name=context.get("model_name", "")
        ),
        choices=[
            SuggestionsResponse.Choice(text=suggestion),
        ],
    )


@timing("get_internal_suggestions_duration_s")
def get_suggestions(
    usecase: CodeSuggestionsUseCaseV2,
    req: SuggestionsRequest,
) -> str:
    return usecase(
        req.current_file.content_above_cursor,
        req.current_file.content_below_cursor,
        req.current_file.file_name,
    )