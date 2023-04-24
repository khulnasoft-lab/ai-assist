from dependency_injector import containers, providers

from codesuggestions.auth import GitLabAuthProvider, BasicAuthProvider
from codesuggestions.api import middleware
from codesuggestions.models import grpc_connect_triton, vertex_ai_connect, Codegen, PalmTextGenModel
from codesuggestions.suggestions import CodeSuggestionsUseCase
from codesuggestions.generative import PalmTextGenUseCase

__all__ = [
    "FastApiContainer",
    "CodeSuggestionsContainer",
    "GenerativeAiContainer",
]

_PROBS_ENDPOINTS = [
    "/monitoring/healthz"
]

_AUTH_SCHEMA_CODE_SUGGESTIONS = "bearer"
_AUTH_SCHEMA_GENERATIVE_AI = "basic"


def _init_triton_grpc_client(host: str, port: int):
    client = grpc_connect_triton(host, port)
    yield client
    client.close()


def _init_vertex_ai_client(api_endpoint: str):
    client = vertex_ai_connect(api_endpoint)
    yield client
    client.transport.close()


class FastApiContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=["codesuggestions.api.server"])

    config = providers.Configuration()

    auth_provider = providers.Singleton(
        GitLabAuthProvider,
        base_url=config.auth.gitlab_api_base_url,
    )

    auth_middleware = providers.Factory(
        middleware.MiddlewareAuthentication,
        auth_provider,
        bypass_auth=config.auth.bypass,
        skip_endpoints=_PROBS_ENDPOINTS,
        schema=_AUTH_SCHEMA_CODE_SUGGESTIONS,
    )

    log_middleware = providers.Factory(
        middleware.MiddlewareLogRequest,
        skip_endpoints=_PROBS_ENDPOINTS,
    )


class CodeSuggestionsContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "codesuggestions.api.suggestions",
            "codesuggestions.api.v2.endpoints.suggestions",
            "codesuggestions.api.monitoring",
        ]
    )

    config = providers.Configuration()

    grpc_client = providers.Resource(
        _init_triton_grpc_client,
        host=config.triton.host,
        port=config.triton.port,
    )

    model_codegen = providers.Singleton(
        Codegen,
        grpc_client=grpc_client,
    )

    usecase = providers.Singleton(
        CodeSuggestionsUseCase,
        model=model_codegen,
    )


class GenerativeAiContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "codesuggestions.api.v2.endpoints.generative",
            "codesuggestions.api.server",
        ]
    )

    config = providers.Configuration()

    auth_provider = providers.Singleton(
        BasicAuthProvider,
        username=config.basic_auth_generative_ai.username,
        password=config.basic_auth_generative_ai.password,
    )

    auth_middleware = providers.Singleton(
        middleware.MiddlewareAuthentication,
        auth_provider,
        bypass_auth=config.auth.bypass,
        schema=_AUTH_SCHEMA_GENERATIVE_AI,
    )

    vertex_client = providers.Resource(
        _init_vertex_ai_client,
        api_endpoint=config.palm_text_model.api_endpoint,
    )

    palm_text_model = providers.Singleton(
        PalmTextGenModel,
        client=vertex_client,
        project=config.palm_text_model.project,
        location=config.palm_text_model.location,
        endpoint_id=config.palm_text_model.endpoint_id,
    )

    palm_text_usecase = providers.Singleton(
        PalmTextGenUseCase,
        text_model=palm_text_model,
    )
