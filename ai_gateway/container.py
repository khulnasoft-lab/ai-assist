from dependency_injector import containers, providers
from py_grpc_prometheus.prometheus_client_interceptor import PromClientInterceptor

from ai_gateway.chat.container import ContainerChat
from ai_gateway.code_suggestions.container import ContainerCodeSuggestions
from ai_gateway.models.container import ContainerModels
from ai_gateway.tracking.container import ContainerTracking

__all__ = [
    "ContainerApplication",
]

from ai_gateway.x_ray.container import ContainerXRay


class ContainerApplication(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "ai_gateway.api.v1.x_ray.libraries",
            "ai_gateway.api.v1.chat.agent",
            "ai_gateway.api.v2.code.completions",
            "ai_gateway.api.v3.code.completions",
            "ai_gateway.api.server",
            "ai_gateway.api.monitoring",
            "ai_gateway.async_dependency_resolver",
        ]
    )

    config = providers.Configuration(strict=True)

    interceptor = providers.Resource(
        PromClientInterceptor,
        enable_client_handling_time_histogram=True,
        enable_client_stream_receive_time_histogram=True,
        enable_client_stream_send_time_histogram=True,
    )

    snowplow = providers.Container(ContainerTracking, config=config.snowplow)

    pkg_models = providers.Container(
        ContainerModels,
        config=config,
    )
    code_suggestions = providers.Container(
        ContainerCodeSuggestions,
        models=pkg_models,
        config=config.f.code_suggestions,
        snowplow=snowplow,
    )
    x_ray = providers.Container(
        ContainerXRay,
        models=pkg_models,
    )
    chat = providers.Container(
        ContainerChat,
        models=pkg_models,
    )

    snowplow = providers.Container(ContainerTracking, config=config.snowplow)
