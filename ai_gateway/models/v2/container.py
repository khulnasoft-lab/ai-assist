from dependency_injector import containers, providers

__all__ = [
    "ContainerModels",
]


class ContainerModels(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)
