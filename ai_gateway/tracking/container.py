from dependency_injector import containers, providers

from ai_gateway.tracking.instrumentator import SnowplowInstrumentator
from ai_gateway.tracking.snowplow import (
    SnowplowClient,
    SnowplowClientConfiguration,
    SnowplowClientStub,
)

__all__ = [
    "ContainerTracking",
]


def _init_snowplow_client(
    enabled: bool, configuration: SnowplowClientConfiguration
) -> SnowplowClient | SnowplowClientStub:
    if not enabled:
        return SnowplowClientStub()

    return SnowplowClient(configuration)


class ContainerTracking(containers.DeclarativeContainer):
    config = providers.Configuration()

    client = providers.Resource(
        _init_snowplow_client,
        enabled=config.enabled,
        configuration=providers.Resource(
            SnowplowClientConfiguration,
            endpoint=config.endpoint,
        ),
    )

    instrumentator = providers.Resource(
        SnowplowInstrumentator,
        client=client,
    )
