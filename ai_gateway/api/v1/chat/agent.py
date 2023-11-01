from time import time
from typing import Optional

import structlog
from anthropic import AsyncAnthropic
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from pydantic.types import confloat
from starlette.authentication import requires

from ai_gateway.models import (
    AnthropicAPIConnectionError,
    AnthropicAPIStatusError,
    AnthropicModel,
)

__all__ = [
    "router",
]

ANTHROPIC = "anthropic"
SUPPORTED_PROVIDERS = [ANTHROPIC]

log = structlog.stdlib.get_logger("chat")

router = APIRouter(
    prefix="",
    tags=["chat"],
)


class PromptMetadata(BaseModel):
    source: str
    version: str


class PromptPayload(BaseModel):
    content: str
    provider: str
    model: str


class ChatRequest(BaseModel):
    type: str
    metadata: PromptMetadata
    payload: PromptPayload


class ChatResponseMetadata(BaseModel):
    provider: str
    model: str
    timestamp: int


class ChatResponse(BaseModel):
    response: str
    metadata: ChatResponseMetadata


class AnthropicResponse(BaseModel):
    id: str
    created: int
    completion: str = "text_completion"


class AnthropicRequest(BaseModel):
    prompt: str
    model: str = "claude-2"
    max_tokens_to_sample: int = 2048
    stop_sequences: Optional[list] = []
    stream: bool = False
    temperature: Optional[confloat(ge=0.0, le=1.0)] = 0.1


async def anthropic(
    payload: AnthropicRequest,
):
    model = AnthropicModel.from_model_name(
        payload.model,
        AsyncAnthropic(),
    )

    try:
        completion = await model.generate(
            prefix=payload.prompt,
            _suffix="",
            max_tokens_to_sample=payload.max_tokens_to_sample,
            stream=payload.stream,
            temperature=payload.temperature,
            stop_sequences=payload.stop_sequences,
        )

        return AnthropicResponse(
            id="id", created=int(time()), completion=completion.text
        )
    except (AnthropicAPIConnectionError, AnthropicAPIStatusError) as e:
        log.error(f"failed to execute Anthropic request: {e}")


def chat_request_to_anthropic_request(chat_request: ChatRequest):
    payload = chat_request.payload
    return AnthropicRequest(prompt=payload.content, model=payload.model)


def anthropic_response_to_chat_response(
    anthropic_response: AnthropicResponse, anthropic_request: AnthropicRequest
):
    metadata = ChatResponseMetadata(
        provider=ANTHROPIC, model=anthropic_request.model, timestamp=time()
    )

    return ChatResponse(response=anthropic_response.completion, metadata=metadata)


async def obtain_chat_response_from_supported_provider(chat_request):
    # We only support and expect Anthropic for now, no branching here
    anthropic_request = chat_request_to_anthropic_request(chat_request)
    anthropic_response = await anthropic(anthropic_request)

    if anthropic_response:
        chat_response = anthropic_response_to_chat_response(
            anthropic_response, anthropic_request
        )
        return chat_response
    else:
        raise HTTPException(
            status_code=500, detail="Failed to obtain Anthropic response"
        )


@router.post("/agent", response_model=ChatResponse)
@requires("duo_chat")
async def chat(request: Request, chat_request: ChatRequest):
    requested_provider = chat_request.payload.provider

    if requested_provider not in SUPPORTED_PROVIDERS:
        log.error(f"Unsupported provider: {requested_provider}")
        raise HTTPException(status_code=422, detail="Unsupported provider")

    return await obtain_chat_response_from_supported_provider(chat_request)
