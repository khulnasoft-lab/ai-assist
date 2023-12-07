from time import time
from typing import Optional

import structlog
from anthropic import APIConnectionError, APIStatusError, AsyncAnthropic
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langchain.chat_models import ChatAnthropic
from langchain.schema import StrOutputParser
from pydantic import BaseModel
from pydantic.types import conlist, constr
from pydantic.typing import Literal
from starlette.authentication import requires

from ai_gateway.deps import ChatContainer
from ai_gateway.models import AnthropicModel

__all__ = [
    "router",
]

ANTHROPIC = "anthropic"

log = structlog.stdlib.get_logger("chat")

router = APIRouter(
    prefix="",
    tags=["chat"],
)


class PromptMetadata(BaseModel):
    source: constr(max_length=100)
    version: constr(max_length=100)


class PromptPayload(BaseModel):
    content: constr(max_length=400000)
    provider: Optional[
        Literal[ANTHROPIC]
    ]  # We only support and expect Anthropic for now
    model: Optional[
        Literal[AnthropicModel.CLAUDE, AnthropicModel.CLAUDE_INSTANT]
    ] = AnthropicModel.CLAUDE


class PromptComponent(BaseModel):
    type: constr(max_length=100)
    metadata: PromptMetadata
    payload: PromptPayload


# We expect only a single prompt component in the first iteration.
# Details: https://gitlab.com/gitlab-org/gitlab/-/merge_requests/135837#note_1642865693
class ChatRequest(BaseModel):
    prompt_components: conlist(PromptComponent, min_items=1, max_items=1)
    stream: Optional[bool] = False


class ChatResponseMetadata(BaseModel):
    provider: str
    model: str
    timestamp: int


class ChatResponse(BaseModel):
    response: str
    metadata: ChatResponseMetadata


@router.post("/agent", response_model=ChatResponse)
@requires("duo_chat")
@inject
async def chat(
    request: Request,
    chat_request: ChatRequest,
    anthropic_client: AsyncAnthropic = Depends(Provide[ChatContainer.anthropic_client]),
):
    prompt_component = chat_request.prompt_components[0]
    payload = prompt_component.payload

    chain = (
        ChatAnthropic(model_name=payload.model, async_client=anthropic_client)
        | StrOutputParser()
    )

    if chat_request.stream:
        return StreamingResponse(
            chain.astream(payload.content), media_type="text/event-stream"
        )

    try:
        if completion := await chain.ainvoke(payload.content):
            return ChatResponse(
                response=completion,
                metadata=ChatResponseMetadata(
                    provider=ANTHROPIC, model=payload.model, timestamp=time()
                ),
            )
    except (APIConnectionError, APIStatusError) as ex:
        log.error(f"failed to execute Anthropic request: {ex}")
    return ChatResponse(
        response="",
        metadata=ChatResponseMetadata(
            provider=ANTHROPIC, model=payload.model, timestamp=time()
        ),
    )
