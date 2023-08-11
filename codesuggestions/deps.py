from pathlib import Path

from dependency_injector import containers, providers
from py_grpc_prometheus.prometheus_client_interceptor import PromClientInterceptor

from codesuggestions.api import middleware
from codesuggestions.api.rollout.model import ModelRollout, ModelRolloutWithFallbackPlan
from codesuggestions.auth import GitLabAuthProvider, GitLabOidcProvider
from codesuggestions.experiments.registry import create_experiment_registry_provider
from codesuggestions.models import (
    FakeGitLabCodeGenModel,
    FakePalmTextGenModel,
    GitLabCodeGen,
    PalmCodeGenModel,
    grpc_connect_triton,
    grpc_connect_vertex,
)
from codesuggestions.suggestions import CodeSuggestions
from codesuggestions.suggestions.processing import ModelEngineCodegen, ModelEnginePalm
from codesuggestions.tokenizer import init_tokenizer

__all__ = [
    "FastApiContainer",
    "CodeSuggestionsContainer",
]

_PROBS_ENDPOINTS = ["/monitoring/healthz", "/metrics"]


def _init_triton_grpc_client(host: str, port: int, interceptor: PromClientInterceptor):
    client = grpc_connect_triton(host, port, interceptor)
    yield client
    client.close()


def _init_vertex_grpc_client(api_endpoint: str, real_or_fake):
    if real_or_fake == "fake":
        yield None
        return

    client = grpc_connect_vertex(
        {
            "api_endpoint": api_endpoint,
        }
    )
    yield client
    client.transport.close()


def _create_gitlab_codegen_model_provider(grpc_client_triton, real_or_fake):
    return providers.Selector(
        real_or_fake,
        real=providers.Singleton(
            GitLabCodeGen,
            grpc_client=grpc_client_triton,
        ),
        fake=providers.Singleton(FakeGitLabCodeGenModel),
    )


def _create_palm_engine_providers(
    grpc_client_vertex, tokenizer, project, location, real_or_fake, experiment_registry
):
    model_names = [
        ModelRollout.GOOGLE_TEXT_BISON,
        ModelRollout.GOOGLE_CODE_BISON,
        ModelRollout.GOOGLE_CODE_GECKO,
    ]

    models = {
        name: providers.Selector(
            real_or_fake,
            real=providers.Singleton(
                PalmCodeGenModel.from_model_name,
                client=grpc_client_vertex,
                project=project,
                location=location,
                name=name,
            ),
            fake=providers.Singleton(FakePalmTextGenModel),
        )
        for name in model_names
    }

    return {
        name: providers.Factory(
            ModelEnginePalm,
            model=model,
            tokenizer=tokenizer,
            experiment_registry=experiment_registry,
        )
        for name, model in models.items()
    }


class FastApiContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=["codesuggestions.api.server"]
    )

    config = providers.Configuration()

    auth_provider = providers.Singleton(
        GitLabAuthProvider,
        base_url=config.auth.gitlab_api_base_url,
    )

    oidc_provider = providers.Singleton(
        GitLabOidcProvider,
        oidc_providers=providers.Dict(
            {
                "Gitlab": config.auth.gitlab_base_url,
                "CustomersDot": config.auth.customer_portal_base_url,
            }
        ),
    )

    auth_middleware = providers.Factory(
        middleware.MiddlewareAuthentication,
        auth_provider,
        oidc_provider,
        bypass_auth=config.auth.bypass,
        skip_endpoints=_PROBS_ENDPOINTS,
    )

    log_middleware = providers.Factory(
        middleware.MiddlewareLogRequest,
        skip_endpoints=_PROBS_ENDPOINTS,
    )

    telemetry_middleware = providers.Factory(
        middleware.MiddlewareModelTelemetry,
        skip_endpoints=_PROBS_ENDPOINTS,
    )


class CodeSuggestionsContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "codesuggestions.api.v2.endpoints.code",
            "codesuggestions.api.v2.experimental.code",
            "codesuggestions.api.monitoring",
        ]
    )

    config = providers.Configuration()

    interceptor = providers.Resource(
        PromClientInterceptor,
        enable_client_handling_time_histogram=True,
        enable_client_stream_receive_time_histogram=True,
        enable_client_stream_send_time_histogram=True,
    )

    grpc_client_triton = providers.Resource(
        _init_triton_grpc_client,
        host=config.triton.host,
        port=config.triton.port,
        interceptor=interceptor,
    )

    grpc_client_vertex = providers.Resource(
        _init_vertex_grpc_client,
        api_endpoint=config.palm_text_model.vertex_api_endpoint,
        real_or_fake=config.palm_text_model.real_or_fake,
    )

    tokenizer = providers.Resource(init_tokenizer)

    palm_model_rollout = providers.Callable(
        # take the first model only as the primary one if several passed
        lambda model_names: ModelRollout(model_names[0]),
        model_names=config.palm_text_model.names,
    )

    model_rollout_plan = providers.Resource(
        ModelRolloutWithFallbackPlan,
        rollout_percentage=config.feature_flags.third_party_rollout_percentage,
        primary_model=palm_model_rollout,
        fallback_model=ModelRollout.GITLAB_CODEGEN,
    )

    model_gitlab_codegen = _create_gitlab_codegen_model_provider(
        grpc_client_triton,
        config.gitlab_codegen_model.real_or_fake,
    )

    experiment_registry = create_experiment_registry_provider()

    engines_palm_codegen = _create_palm_engine_providers(
        grpc_client_vertex,
        tokenizer,
        config.palm_text_model.project,
        config.palm_text_model.location,
        config.palm_text_model.real_or_fake,
        experiment_registry,
    )

    engine_codegen_factory_template = providers.Callable(
        ModelEngineCodegen.from_local_templates,
        tpl_dir=Path(__file__).parent / "_assets" / "tpl" / "codegen",
    )

    engine_factory = providers.FactoryAggregate(
        **{
            ModelRollout.GITLAB_CODEGEN: providers.Factory(
                engine_codegen_factory_template,
                model=model_gitlab_codegen,
            ),
            **{
                ModelRollout(name): engine
                for name, engine in engines_palm_codegen.items()
            },
        }
    )

    code_suggestions = providers.Factory(
        CodeSuggestions,
    )
