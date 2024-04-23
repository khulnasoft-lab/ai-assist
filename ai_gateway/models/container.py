import os
from typing import Iterator, Optional

from anthropic import AsyncAnthropic
from dependency_injector import containers, providers
from google.cloud.aiplatform.gapic import PredictionServiceAsyncClient

from ai_gateway.models import mock
from ai_gateway.models.anthropic import AnthropicChatModel, AnthropicModel
from ai_gateway.models.base import connect_anthropic, grpc_connect_vertex
from ai_gateway.models.litellm import LiteLLMChatModel, LiteLlmModel
from ai_gateway.models.vertex_text import (
    PalmCodeBisonModel,
    PalmCodeGeckoModel,
    PalmTextBisonModel,
)

__all__ = [
    "ContainerModels",
]


def _init_vertex_grpc_client(
    endpoint: str, mock_model_responses: bool, json_key: str = ""
) -> Iterator[Optional[PredictionServiceAsyncClient]]:
    if mock_model_responses:
        yield None
        return

    if json_key:
        with open("/tmp/vertex-client.json", "w") as f:
            f.write(json_key)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/vertex-client.json"

    client = grpc_connect_vertex({"api_endpoint": endpoint})
    yield client
    client.transport.close()


def _init_anthropic_client(
    mock_model_responses: bool,
) -> Iterator[Optional[AsyncAnthropic]]:
    if mock_model_responses:
        yield None
        return

    client = connect_anthropic()
    yield client
    client.close()


class ContainerModels(containers.DeclarativeContainer):
    # We need to resolve the model based on the model name provided by the upstream container.
    # Hence, `VertexTextBaseModel.from_model_name` and `AnthropicModel.from_model_name` are only partially applied here.

    config = providers.Configuration(strict=True)

    _mock_selector = providers.Callable(
        lambda mock_model_responses: "mocked" if mock_model_responses else "original",
        config.mock_model_responses,
    )

    grpc_client_vertex = providers.Resource(
        _init_vertex_grpc_client,
        endpoint=config.vertex_text_model.endpoint,
        mock_model_responses=config.mock_model_responses,
        json_key=config.vertex_text_model.json_key,
    )

    http_client_anthropic = providers.Resource(
        _init_anthropic_client,
        mock_model_responses=config.mock_model_responses,
    )

    vertex_text_bison = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            PalmTextBisonModel.from_model_name,
            client=grpc_client_vertex,
            project=config.vertex_text_model.project,
            location=config.vertex_text_model.location,
        ),
        mocked=providers.Factory(mock.LLM),
    )

    vertex_code_bison = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            PalmCodeBisonModel.from_model_name,
            client=grpc_client_vertex,
            project=config.vertex_text_model.project,
            location=config.vertex_text_model.location,
        ),
        mocked=providers.Factory(mock.LLM),
    )

    vertex_code_gecko = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            PalmCodeGeckoModel.from_model_name,
            client=grpc_client_vertex,
            project=config.vertex_text_model.project,
            location=config.vertex_text_model.location,
        ),
        mocked=providers.Factory(mock.LLM),
    )

    # anthropic_claude = providers.Selector(
    #     _mock_selector,
    #     original=providers.Factory(
    #         AnthropicModel.from_model_name, client=http_client_anthropic
    #     ),
    #     mocked=providers.Factory(mock.LLM),
    # )

    anthropic_claude = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            LiteLlmModel.create
        ),
        mocked=providers.Factory(mock.LLM),
    )

    # anthropic_claude_chat = providers.Selector(
    #     _mock_selector,
    #     original=providers.Factory(
    #         AnthropicChatModel.from_model_name,
    #         client=http_client_anthropic,
    #     ),
    #     mocked=providers.Factory(mock.ChatModel),
    # )

    anthropic_claude_chat = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            LiteLLMChatModel.create,
        ),
        mocked=providers.Factory(mock.ChatModel),
    )
