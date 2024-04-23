import os
import structlog
from fastapi import APIRouter, Depends, Request
from starlette.authentication import requires

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v1.autodev.typing import AutodevRequest, AutodevResponse
from ai_gateway.api.v1.autodev.anthropic_client import AnthropicClient

from ai_gateway.models import (
    AnthropicAPIConnectionError,
    AnthropicAPIStatusError
)
from ai_gateway.tracking.errors import log_exception

import autogen
from autogen import AssistantAgent, UserProxyAgent

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("autodev")

router = APIRouter()


@router.post("/issues", response_model=AutodevResponse)
# @requires("code_suggestions")
# @feature_category("code_suggestions")
async def issues(
    request: Request,
    payload: AutodevRequest,
):
    anthropic_llm_config =     {
        # Choose your model name.
        "model": "claude-3-sonnet-20240229",
        # You need to provide your API key here.
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "base_url": "https://api.anthropic.com",
        "api_type": "anthropic",
        "model_client_cls": "AnthropicClient",
    }

    assistant = AssistantAgent("assistant", llm_config=anthropic_llm_config)
    assistant.register_model_client(model_client_cls=AnthropicClient)


    user_proxy = UserProxyAgent(
        "user_proxy",
        human_input_mode="NEVER", 
        code_execution_config={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        max_consecutive_auto_reply=1,
    )
    result = user_proxy.initiate_chat(
        assistant,
        message="Plot a chart of NVDA and TESLA stock price change YTD.",
    )

    return AutodevResponse(response=result.summary)
