from dependency_injector import containers, providers

from ai_gateway.chains.config import ModelClassProvider
from ai_gateway.chains.registry import CustomModelsChainRegistry, LocalChainRegistry
from ai_gateway.chat import agents as chat

__all__ = [
    "ContainerChains",
]


class ContainerChains(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)
    models = providers.DependenciesContainer()

    _registry_params = {
        "model_factories": {
            ModelClassProvider.ANTHROPIC: providers.Factory(
                models.anthropic_claude_chat_fn
            ),
            ModelClassProvider.LITE_LLM: providers.Factory(models.lite_llm_chat_fn),
        },
        "class_overrides": {
            "chat/react": chat.ReActAgent,
            "chat/react-custom": chat.ReActAgent,
        },
    }

    _custom_models_or_local = providers.Callable(
        lambda custom_models_enabled: (
            "custom_models" if custom_models_enabled else "local"
        ),
        config.custom_models.enabled,
    )

    _chain_registry_factory = providers.Selector(
        _custom_models_or_local,
        custom_models=providers.Factory(
            CustomModelsChainRegistry.from_local_yaml, **_registry_params
        ),
        local=providers.Factory(LocalChainRegistry.from_local_yaml, **_registry_params),
    )

    chain_registry = providers.Singleton(_chain_registry_factory)
