from dependency_injector import containers, providers
from py_grpc_prometheus.prometheus_client_interceptor import PromClientInterceptor

from ai_gateway.abuse_detection.container import ContainerAbuseDetection
from ai_gateway.agents.container import ContainerAgents, SelfHostedContainerAgents
from ai_gateway.auth.container import ContainerSelfSignedJwt
from ai_gateway.chat.container import ContainerChat, SelfHostedContainerChat
from ai_gateway.code_suggestions.container import (
    ContainerCodeSuggestions,
    SelfHostedContainerCodeSuggestions,
)
from ai_gateway.models.container import ContainerModels, SelfHostedContainerModels
from ai_gateway.models.v2.container import (
    ContainerModels as ContainerModelsV2,
    SelfHostedContainerModels as SelfHostedContainerModelsV2,
)
from ai_gateway.searches.container import ContainerSearches, SelfHostedContainerSearches
from ai_gateway.tracking.container import ContainerTracking, SelfHostedContainerTracking

__all__ = [
    "ContainerApplication",
]

from ai_gateway.x_ray.container import ContainerXRay

SELF_HOSTED_CONTAINERS = {
    "chat": SelfHostedContainerChat,
    "code_suggestions": SelfHostedContainerCodeSuggestions,
    "pkg_agents": SelfHostedContainerAgents,
    "pkg_models": SelfHostedContainerModels,
    "pkg_models_v2": SelfHostedContainerModelsV2,
    "searches": SelfHostedContainerSearches,
    "tracking": SelfHostedContainerTracking,
    "x_ray": ContainerXRay,
}

GITLAB_HOSTED_CONTAINERS = {
    "chat": ContainerChat,
    "code_suggestions": ContainerCodeSuggestions,
    "pkg_agents": ContainerAgents,
    "pkg_models": ContainerModels,
    "pkg_models_v2": ContainerModelsV2,
    "searches": ContainerSearches,
    "tracking": ContainerTracking,
    "x_ray": ContainerXRay,
}


class ContainerApplication(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "ai_gateway.api.v1.x_ray.libraries",
            "ai_gateway.api.v1.chat.agent",
            "ai_gateway.api.v1.search.docs",
            "ai_gateway.api.v2.code.completions",
            "ai_gateway.api.v3.code.completions",
            "ai_gateway.api.server",
            "ai_gateway.api.monitoring",
            "ai_gateway.async_dependency_resolver",
        ]
    )

    config = providers.Configuration(strict=True)

    interceptor: providers.Resource = providers.Resource(
        PromClientInterceptor,
        enable_client_handling_time_histogram=True,
        enable_client_stream_receive_time_histogram=True,
        enable_client_stream_send_time_histogram=True,
    )

    _containers = (
        SELF_HOSTED_CONTAINERS if config.self_hosted else GITLAB_HOSTED_CONTAINERS
    )

    snowplow = providers.Container(_containers["tracking"], config=config.snowplow)

    searches = providers.Container(_containers["searches"], config=config)

    pkg_models = providers.Container(_containers["pkg_models"], config=config)

    pkg_models_v2 = providers.Container(_containers["pkg_models_v2"], config=config)

    pkg_agents = providers.Container(
        _containers["pkg_agents"], models=pkg_models_v2, config=config
    )

    chat = providers.Container(_containers["chat"], models=pkg_models)

    code_suggestions = providers.Container(
        _containers["code_suggestions"],
        models=pkg_models,
        config=config.f.code_suggestions,
        snowplow=snowplow,
    )

    x_ray = providers.Container(
        _containers["x_ray"],
        models=pkg_models,
    )

    self_signed_jwt = providers.Container(
        ContainerSelfSignedJwt,
        config=config,
    )
    abuse_detection = providers.Container(
        ContainerAbuseDetection,
        config=config.abuse_detection,
        models=pkg_models,
    )
