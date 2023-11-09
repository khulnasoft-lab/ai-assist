import os

import structlog
from dotenv import load_dotenv
from fastapi import APIRouter
from langchain.chat_models import ChatAnthropic
from langserve import add_routes

__all__ = ["create_router"]

from ai_gateway.code_suggestions.experimentation.metadata import (
    FileMetadataChainInput,
    FileMetadataChainOutput,
    file_metadata_chain,
)

# TODO: Move model instantiation to deps.py or to a similar module
load_dotenv()

log = structlog.stdlib.get_logger("experimental")


def create_router() -> APIRouter:
    router = APIRouter(tags=["code metadata experimental"], prefix="/code")
    if not os.environ.get("ANTHROPIC_API_KEY", None):
        log.warn(
            "Env ANTHROPIC_API_KEY is not set. "
            "All code metadata experimental endpoints will be disabled."
        )
        return router

    model_anthropic_claude: ChatAnthropic = ChatAnthropic(model="claude-2")

    add_routes(
        router,
        file_metadata_chain(model_anthropic_claude),
        path="/metadata",
        input_type=FileMetadataChainInput,
        output_type=FileMetadataChainOutput,
    )

    return router
