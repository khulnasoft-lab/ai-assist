from time import time
from typing import AsyncIterator

import structlog
from dependency_injector.providers import Factory
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v3.code.typing import (
    CodeEditorComponents,
    CompletionRequest,
    CompletionResponse,
    EditorContentCompletionPayload,
    EditorContentGenerationPayload,
    ModelMetadata,
    ResponseMetadataBase,
    StreamSuggestionsResponse,
)
from ai_gateway.auth.authentication import requires
from ai_gateway.code_suggestions import (
    CodeCompletions,
    CodeCompletionsLegacy,
    CodeGenerations,
    CodeSuggestionsChunk,
    ModelProvider,
    PiiRedactor,
)
from ai_gateway.deps import CodeSuggestionsContainer

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("codesuggestions")

router = APIRouter()


@router.post("/completions")
@requires("code_suggestions")
@feature_category("code_suggestions")
async def completions(
    request: Request,
    payload: CompletionRequest,
):
    component = payload.prompt_components[0]
    if component.type == CodeEditorComponents.COMPLETION:
        return await code_completion(payload=component.payload)
    if component.type == CodeEditorComponents.GENERATION:
        return await code_generation(payload=component.payload)


@inject
async def code_completion(
    payload: EditorContentCompletionPayload,
    code_completions_legacy: Factory[CodeCompletionsLegacy] = Depends(
        Provide[CodeSuggestionsContainer.code_completions_legacy.provider]
    ),
    code_completions_anthropic: Factory[CodeCompletions] = Depends(
        Provide[CodeSuggestionsContainer.code_completions_anthropic.provider]
    ),
):
    payload.content_above_cursor = redact_pii(payload.content_above_cursor)
    payload.content_below_cursor = redact_pii(payload.content_below_cursor)

    if payload.model_provider == ModelProvider.ANTHROPIC:
        engine = code_completions_anthropic()
    else:
        engine = code_completions_legacy()

    suggestion = await engine.execute(
        prefix=payload.content_above_cursor,
        suffix=payload.content_below_cursor,
        file_name=payload.file_name,
        editor_lang=payload.language_identifier,
        stream=payload.stream,
    )

    if isinstance(suggestion, AsyncIterator):
        return await _handle_stream(suggestion)

    return CompletionResponse(
        response=suggestion.text,
        metadata=ResponseMetadataBase(
            timestamp=int(time()),
            model=ModelMetadata(
                engine=suggestion.model.engine,
                name=suggestion.model.name,
                lang=suggestion.lang,
            ),
        ),
    )


@inject
async def code_generation(
    payload: EditorContentGenerationPayload,
    code_generations_vertex: Factory[CodeGenerations] = Depends(
        Provide[CodeSuggestionsContainer.code_generations_vertex.provider]
    ),
    code_generations_anthropic: Factory[CodeGenerations] = Depends(
        Provide[CodeSuggestionsContainer.code_generations_anthropic.provider]
    ),
):
    payload.content_above_cursor = redact_pii(payload.content_above_cursor)
    payload.content_below_cursor = redact_pii(payload.content_below_cursor)

    if payload.model_provider == ModelProvider.ANTHROPIC:
        engine = code_generations_anthropic()
    else:
        engine = code_generations_vertex()

    if payload.prompt:
        engine.with_prompt_prepared(payload.prompt)

    suggestion = await engine.execute(
        prefix=payload.content_above_cursor,
        file_name=payload.file_name,
        editor_lang=payload.language_identifier,
        model_provider=payload.model_provider,
        stream=payload.stream,
    )

    if isinstance(suggestion, AsyncIterator):
        return await _handle_stream(suggestion)

    return CompletionResponse(
        response=suggestion.text,
        metadata=ResponseMetadataBase(
            timestamp=int(time()),
            model=ModelMetadata(
                engine=suggestion.model.engine,
                name=suggestion.model.name,
                lang=suggestion.lang,
            ),
        ),
    )


async def _handle_stream(
    response: AsyncIterator[CodeSuggestionsChunk],
) -> StreamSuggestionsResponse:
    async def _stream_generator():
        async for result in response:
            yield result.text

    return StreamSuggestionsResponse(
        _stream_generator(), media_type="text/event-stream"
    )


@inject
def redact_pii(
    content: str,
    pii_redactor: PiiRedactor = Depends(Provide[CodeSuggestionsContainer.pii_redactor]),
) -> (str, str):
    return pii_redactor.redact_pii(content=content)
