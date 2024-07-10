from dependency_injector import containers, providers

from ai_gateway.agents.config import ModelClassProvider
from ai_gateway.agents.registry import CustomModelsAgentRegistry, LocalAgentRegistry
from ai_gateway.chat import agents as chat

__all__ = ["ContainerAgents", "SelfHostedContainerAgents"]


class ContainerAgents(containers.DeclarativeContainer):
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

    _agent_registry_factory = local=providers.Factory(LocalAgentRegistry.from_local_yaml, **_registry_params)

    agent_registry = providers.Singleton(_agent_registry_factory)


class SelfHostedContainerAgents(containers.DeclarativeContainer):
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

    _anthropic_claude_fn = providers.Callable(lambda: None)
    _lite_llm_chat_fn = providers.Factory(models.lite_llm_chat_fn)

    _agent_registry_factory = providers.Factory(LocalAgentRegistry.from_local_yaml, **_registry_params)

    agent_registry = providers.Singleton(_agent_registry_factory)
