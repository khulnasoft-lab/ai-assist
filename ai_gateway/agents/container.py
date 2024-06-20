from typing import Type

import structlog
from dependency_injector import containers, providers

from ai_gateway.agents import chat
from ai_gateway.agents.base import Agent
from ai_gateway.agents.registry import (
    Key,
    LocalAgentRegistry,
    ModelFactoryType,
    ModelProvider,
)

__all__ = [
    "ContainerAgents",
]

log = structlog.stdlib.get_logger("agent_registry")


def _init_local_agent_registry(
    *,
    data: dict[Key, Type[Agent]],
    model_factories: dict[ModelProvider, ModelFactoryType]
) -> LocalAgentRegistry:
    log.info("Initializing the local agent registry")

    return LocalAgentRegistry.from_local_yaml(data, model_factories)


class ContainerAgents(containers.DeclarativeContainer):
    models = providers.DependenciesContainer()

    _anthropic_claude_fn = providers.Factory(models.anthropic_claude_chat_fn)

    # Resource provider is similar to Singleton.
    # Resource initialization happens only once when invoking the `init_resources` container method.
    # Doc: https://python-dependency-injector.ets-labs.org/providers/resource.html
    agent_registry = providers.Resource(
        _init_local_agent_registry,
        data={Key(use_case="chat", type="react"): chat.ReActAgent},
        model_factories={ModelProvider.ANTHROPIC: _anthropic_claude_fn},
    )
