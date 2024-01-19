from typing import Iterator, Optional

from anthropic import AsyncAnthropic
from dependency_injector import containers, providers
from google.cloud.aiplatform.gapic import PredictionServiceAsyncClient

from ai_gateway.models.anthropic import AnthropicModel
from ai_gateway.models.custom import CustomModel
from ai_gateway.models.base import connect_anthropic, grpc_connect_vertex, connect_custom_models
from ai_gateway.models.fake import FakePalmTextGenModel
from ai_gateway.models.vertex_text import (
    PalmCodeBisonModel,
    PalmCodeGeckoModel,
    PalmTextBisonModel,
)

__all__ = [
    "ContainerModels",
]


def _real_or_fake(use_fake: bool) -> str:
    return "fake" if use_fake else "real"


def _init_vertex_grpc_client(
    endpoint: str, use_fake: bool
) -> Iterator[Optional[PredictionServiceAsyncClient]]:
    if use_fake:
        yield None
        return

    client = grpc_connect_vertex({"api_endpoint": endpoint})
    yield client
    client.transport.close()


def _init_anthropic_client(use_fake: bool) -> Iterator[Optional[AsyncAnthropic]]:
    if use_fake:
        yield None
        return

    client = connect_anthropic()
    yield client
    client.close()

def _init_custom_models_client(use_fake: bool) -> Iterator[Optional[AsyncAnthropic]]:
    if use_fake:
        yield None
        return

    client = connect_custom_models()
    yield client
    client.close()

class ContainerModels(containers.DeclarativeContainer):
    # We need to resolve the model based on the model name provided by the upstream container.
    # Hence, `VertexTextBaseModel.from_model_name` and `AnthropicModel.from_model_name` are only partially applied here.

    config = providers.Configuration(strict=True)

    real_or_fake = providers.Callable(_real_or_fake, config.use_fake_models)

    grpc_client_vertex = providers.Resource(
        _init_vertex_grpc_client,
        endpoint=config.vertex_text_model.endpoint,
        use_fake=config.use_fake_models,
    )

    http_client_anthropic = providers.Resource(
        _init_anthropic_client, use_fake=config.use_fake_models
    )

    http_client_custom_models = providers.Resource(
        _init_custom_models_client, use_fake=config.use_fake_models
    )

    vertex_text_bison = providers.Selector(
        real_or_fake,
        real=providers.Factory(
            PalmTextBisonModel.from_model_name,
            client=grpc_client_vertex,
            project=config.vertex_text_model.project,
            location=config.vertex_text_model.location,
        ),
        fake=providers.Factory(FakePalmTextGenModel),
    )

    vertex_code_bison = providers.Selector(
        real_or_fake,
        real=providers.Factory(
            PalmCodeBisonModel.from_model_name,
            client=grpc_client_vertex,
            project=config.vertex_text_model.project,
            location=config.vertex_text_model.location,
        ),
        fake=providers.Factory(FakePalmTextGenModel),
    )

    vertex_code_gecko = providers.Selector(
        real_or_fake,
        real=providers.Factory(
            PalmCodeGeckoModel.from_model_name,
            client=grpc_client_vertex,
            project=config.vertex_text_model.project,
            location=config.vertex_text_model.location,
        ),
        fake=providers.Factory(FakePalmTextGenModel),
    )

    anthropic_claude = providers.Selector(
        real_or_fake,
        real=providers.Factory(
            AnthropicModel.from_model_name,
            client=http_client_anthropic,
        ),
        # TODO: We need to update our fake models to make them generic
        fake=providers.Factory(FakePalmTextGenModel),
    )

    custom_model = providers.Selector(
        real_or_fake,
        real=providers.Factory(
            CustomModel.from_model_name,
            client=http_client_custom_models,
            prompt_template=config.custom_models.prompt_template,
            url=config.custom_models.endpoint,
        ),
        fake=providers.Factory(FakePalmTextGenModel),
    )
