from time import time
from typing import Literal, Optional

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from pydantic.types import confloat, conlist, constr
from starlette.authentication import requires

from ai_gateway.deps import AnthropicContainer
from ai_gateway.models import AnthropicModel

__all__ = [
    "router",
]

router = APIRouter(
    prefix="",
    tags=["anthropic"],
)


class AnthropicResponse(BaseModel):
    id: str
    created: int
    completion: str = None


class AnthropicRequest(BaseModel):
    prompt: str
    model: Optional[
        Literal[AnthropicModel.CLAUDE, AnthropicModel.CLAUDE_INSTANT]
    ] = AnthropicModel.CLAUDE
    max_tokens_to_sample: int = 2048
    stop_sequences: Optional[conlist(constr(max_length=100), max_items=10)] = []
    stream: bool = False
    temperature: Optional[confloat(ge=0.0, le=1.0)] = 0.1


@router.post("/anthropic", response_model=AnthropicResponse)
@requires("duo_chat")
@inject
async def anthropic(
    request: Request,
    payload: AnthropicRequest,
    anthropic_model: AnthropicModel = Depends(
        Provide[AnthropicContainer.anthropic_model]
    ),
):
    model = anthropic_model.provider(model_name=payload.model)

    completion = await model.generate(
        prefix=payload.prompt,
        _suffix="",
        max_tokens_to_sample=payload.max_tokens_to_sample,
        stream=payload.stream,
        temperature=payload.temperature,
        stop_sequences=payload.stop_sequences,
    )

    return AnthropicResponse(id="id", created=int(time()), completion=completion.text)
