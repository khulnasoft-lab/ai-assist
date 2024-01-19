from time import time
from typing import Annotated, AsyncIterator, Union

import anthropic
import structlog
from dependency_injector.providers import Factory
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Body, Depends, Request
from starlette.datastructures import CommaSeparatedStrings

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.middleware import (
    X_GITLAB_GLOBAL_USER_ID_HEADER,
    X_GITLAB_HOST_NAME_HEADER,
    X_GITLAB_INSTANCE_ID_HEADER,
    X_GITLAB_REALM_HEADER,
    X_GITLAB_SAAS_NAMESPACE_IDS_HEADER,
)
from ai_gateway.api.v2.code.typing import (
    CompletionsRequestV1,
    CompletionsRequestV2,
    GenerationsRequestV1,
    GenerationsRequestV2,
    StreamSuggestionsResponse,
    SuggestionsRequest,
    SuggestionsResponse,
)
from ai_gateway.auth.authentication import requires
from ai_gateway.code_suggestions import (
    CodeCompletions,
    CodeCompletionsLegacy,
    CodeGenerations,
    CodeSuggestionsChunk,
)
from ai_gateway.code_suggestions.processing.ops import lang_from_filename
from ai_gateway.container import ContainerApplication
from ai_gateway.instrumentators.base import TelemetryInstrumentator
from ai_gateway.models import KindAnthropicModel, KindModelProvider
from ai_gateway.tracking.errors import log_exception
from ai_gateway.tracking.instrumentator import SnowplowInstrumentator

__all__ = [
    "router",
]


log = structlog.stdlib.get_logger("codesuggestions")

router = APIRouter()

CompletionsRequestWithVersion = Annotated[
    Union[CompletionsRequestV1, CompletionsRequestV2],
    Body(discriminator="prompt_version"),
]

GenerationsRequestWithVersion = Annotated[
    Union[GenerationsRequestV1, GenerationsRequestV2],
    Body(discriminator="prompt_version"),
]


@router.post("/completions")
@router.post("/code/completions")
@requires("code_suggestions")
@feature_category("code_suggestions")
@inject
async def completions(
    request: Request,
    payload: CompletionsRequestWithVersion,
    completions_legacy_factory: Factory[CodeCompletionsLegacy] = Depends(
        Provide[
            ContainerApplication.code_suggestions.completions.vertex_legacy.provider
        ]
    ),
    completions_anthropic_factory: Factory[CodeCompletions] = Depends(
        Provide[ContainerApplication.code_suggestions.completions.anthropic.provider]
    ),
    completions_custom_model_factory: Factory[CodeCompletions] = Depends(
        Provide[ContainerApplication.code_suggestions.completions.custom_model_factory.provider]
    ),
    snowplow_instrumentator: SnowplowInstrumentator = Depends(
        Provide[ContainerApplication.snowplow.instrumentator]
    ),

):
    try:
        track_snowplow_event(request, payload, snowplow_instrumentator)
    except Exception as e:
        log_exception(e)

    log.debug(
        "code completion input:",
        prompt=payload.prompt if hasattr(payload, "prompt") else None,
        prefix=payload.current_file.content_above_cursor,
        suffix=payload.current_file.content_below_cursor,
        current_file_name=payload.current_file.file_name,
        stream=payload.stream,
    )

    kwargs = {}
    if payload.model_provider == KindModelProvider.CUSTOM:
        code_completions = completions_custom_model_factory(
            model__name=payload.model_name)
    elif payload.model_provider == KindModelProvider.ANTHROPIC:
        code_completions = completions_anthropic_factory()

        # We support the prompt version 2 only with the Anthropic models
        if payload.prompt_version == 2:
            kwargs.update({"raw_prompt": payload.prompt})
    else:
        code_completions = completions_legacy_factory()

    with TelemetryInstrumentator().watch(payload.telemetry):
        suggestion = await code_completions.execute(
            prefix=payload.current_file.content_above_cursor,
            suffix=payload.current_file.content_below_cursor,
            file_name=payload.current_file.file_name,
            editor_lang=payload.current_file.language_identifier,
            stream=payload.stream,
            **kwargs,
        )

    if isinstance(suggestion, AsyncIterator):
        return await _handle_stream(suggestion)

    log.debug(
        "code completion suggestion:",
        suggestion=suggestion.text,
        score=suggestion.score,
        language=suggestion.lang,
    )

    return SuggestionsResponse(
        id="id",
        created=int(time()),
        model=SuggestionsResponse.Model(
            engine=suggestion.model.engine,
            name=suggestion.model.name,
            lang=suggestion.lang,
        ),
        experiments=suggestion.metadata.experiments,
        choices=_suggestion_choices(suggestion.text),
    )


@router.post("/code/generations")
@requires("code_suggestions")
@feature_category("code_suggestions")
@inject
async def generations(
    request: Request,
    payload: GenerationsRequestWithVersion,
    generations_vertex_factory: Factory[CodeGenerations] = Depends(
        Provide[ContainerApplication.code_suggestions.generations.vertex.provider]
    ),
    generations_anthropic_factory: Factory[CodeGenerations] = Depends(
        Provide[
            ContainerApplication.code_suggestions.generations.anthropic_factory.provider
        ]
    ),
    snowplow_instrumentator: SnowplowInstrumentator = Depends(
        Provide[ContainerApplication.snowplow.instrumentator]
    ),
):
    try:
        track_snowplow_event(request, payload, snowplow_instrumentator)
    except Exception as e:
        log_exception(e)

    log.debug(
        "code creation input:",
        prompt=payload.prompt if hasattr(payload, "prompt") else None,
        prefix=payload.current_file.content_above_cursor,
        suffix=payload.current_file.content_below_cursor,
        current_file_name=payload.current_file.file_name,
        stream=payload.stream,
    )
    
    if payload.model_provider == KindModelProvider.ANTHROPIC:
        code_generations = _resolve_code_generations_anthropic(
            payload,
            generations_anthropic_factory,
        )
    else:
        code_generations = generations_vertex_factory()

    if payload.prompt_version == 2:
        code_generations.with_prompt_prepared(payload.prompt)

    with TelemetryInstrumentator().watch(payload.telemetry):
        suggestion = await code_generations.execute(
            prefix=payload.current_file.content_above_cursor,
            file_name=payload.current_file.file_name,
            editor_lang=payload.current_file.language_identifier,
            model_provider=payload.model_provider,
            stream=payload.stream,
        )

    if isinstance(suggestion, AsyncIterator):
        return await _handle_stream(suggestion)

    log.debug(
        "code creation suggestion:",
        suggestion=suggestion.text,
        score=suggestion.score,
        language=suggestion.lang,
    )

    return SuggestionsResponse(
        id="id",
        created=int(time()),
        model=SuggestionsResponse.Model(
            engine=suggestion.model.engine,
            name=suggestion.model.name,
            lang=suggestion.lang,
        ),
        choices=_suggestion_choices(suggestion.text),
    )


def _resolve_code_generations_anthropic(
    payload: SuggestionsRequest,
    generations_anthropic_factory: Factory[CodeGenerations],
) -> CodeGenerations:
    model_name = (
        payload.model_name if payload.model_name else KindAnthropicModel.CLAUDE_2_0
    )

    return generations_anthropic_factory(
        model__name=model_name,
        model__stop_sequences=["</new_code>", anthropic.HUMAN_PROMPT],
    )


def _suggestion_choices(text: str) -> list:
    return [SuggestionsResponse.Choice(text=text)] if text else []


def track_snowplow_event(
    req: Request,
    payload: SuggestionsRequest,
    snowplow_instrumentator: SnowplowInstrumentator,
):
    language = lang_from_filename(payload.current_file.file_name) or ""
    if language:
        language = language.name.lower()

    # gitlab-rails 16.3+ sends an X-Gitlab-Realm header
    gitlab_realm = req.headers.get(X_GITLAB_REALM_HEADER)
    # older versions don't serve code suggestions, so we read this from the IDE token claim
    if not gitlab_realm and req.user and req.user.claims:
        gitlab_realm = req.user.claims.gitlab_realm

    snowplow_instrumentator.watch(
        telemetry=payload.telemetry,
        prefix_length=len(payload.current_file.content_above_cursor),
        suffix_length=len(payload.current_file.content_below_cursor),
        language=language,
        user_agent=req.headers.get("User-Agent", ""),
        gitlab_realm=gitlab_realm if gitlab_realm else "",
        gitlab_instance_id=req.headers.get(X_GITLAB_INSTANCE_ID_HEADER, ""),
        gitlab_global_user_id=req.headers.get(X_GITLAB_GLOBAL_USER_ID_HEADER, ""),
        gitlab_host_name=req.headers.get(X_GITLAB_HOST_NAME_HEADER, ""),
        gitlab_saas_namespace_ids=list(
            CommaSeparatedStrings(
                req.headers.get(X_GITLAB_SAAS_NAMESPACE_IDS_HEADER, "")
            )
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
