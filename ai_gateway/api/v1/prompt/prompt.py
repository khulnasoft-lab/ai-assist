import json
from time import time
from typing import AsyncIterator, Union

import requests
import structlog
from dependency_injector.providers import FactoryAggregate
from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.authentication import requires

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v1.prompt.typing import RawRequestBody, RawResponse
from ai_gateway.async_dependency_resolver import (
    get_chat_anthropic_claude_factory_provider,
)
from ai_gateway.models import (
    AnthropicAPIConnectionError,
    AnthropicAPIStatusError,
    AnthropicAPITimeoutError,
    TextGenModelChunk,
    TextGenModelOutput, Message, Role,
)
from ai_gateway.tracking import log_exception
import os

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("prompt")

router = APIRouter()


@router.post("/{prompt_name}/{prompt_version}", response_model=RawResponse, status_code=status.HTTP_200_OK)
@requires("duo_chat")
@feature_category("duo_chat")
async def prompt(
    prompt_name,
    prompt_version,
    request: Request,
    prompt_options: RawRequestBody,
    anthropic_claude_factory: FactoryAggregate = Depends(
        get_chat_anthropic_claude_factory_provider
    ),
):
    json_variables = prompt_options.prompt_components[0].payload.variables

    template = await _fetch_prompt(prompt_name, prompt_version, json_variables)

    completion = await _generate_completion(anthropic_claude_factory, template)

    return RawResponse(response=completion.text)


@router.post("/raw", response_model=RawResponse, status_code=status.HTTP_200_OK)
@requires("duo_chat")
@feature_category("duo_chat")
async def raw(
    request: Request,
    raw_prompt_request: RawRequestBody,
    anthropic_claude_factory: FactoryAggregate = Depends(
        get_chat_anthropic_claude_factory_provider
    ),
):
    template = raw_prompt_request.prompt_components[0].payload.content
    json_variables = raw_prompt_request.prompt_components[0].payload.variables
    # variables = json.loads(json_variables)
    template = template.format(**json_variables)

    completion = await _generate_completion(anthropic_claude_factory, template)

    return RawResponse(response=completion.text)


async def _generate_completion(
    anthropic_claude_factory: FactoryAggregate,
    template: str
) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:
    try:
        opts = {"messages": [Message(role=Role.USER, content=template)], "stream": False}

        completion = await anthropic_claude_factory("chat", name='claude-3-sonnet-20240229').generate(**opts)

        return completion
    except AnthropicAPIStatusError as ex:
        log_exception(ex)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Anthropic API Status Error.",
        )
    except AnthropicAPITimeoutError as ex:
        log_exception(ex)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Anthropic API Timeout Error.",
        )
    except AnthropicAPIConnectionError as ex:
        log_exception(ex)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Anthropic API Connection Error.",
        )


async def _fetch_prompt(prompt_name: str, prompt_version: str, variables: dict) -> str:
    base_url = f'http://localhost:3000/api/v4/projects/19/ai/prompts/compat/langchain/commits/_/{prompt_name}/{prompt_version}'

    request = requests.get(url=base_url, headers={'x-api-key': os.getenv('GITLAB_API_KEY')})

    template = request.json()['manifest']['kwargs']['template']

    template = template.format(**variables)

    return template

#
# async def _generate_completion(
#     anthropic_claude_factory: FactoryAggregate,
#     template: str
# ) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:
#
#     opts = {"messages": [Message(role=Role.USER, content=template)], "stream": False}
#
#     completion = await anthropic_claude_factory("chat", name='claude-3-sonnet-20240229').generate(**opts)
#
#     return completion
