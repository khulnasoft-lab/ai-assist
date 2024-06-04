from dependency_injector import containers, providers

from ai_gateway.agents.chat import ReActAgent
from ai_gateway.agents.generate_description import GenerateDescriptionAgent
from ai_gateway.agents.registry import Key, LocalAgentRegistry

__all__ = [
    "ContainerAgents",
]


class ContainerAgents(containers.DeclarativeContainer):
    agent_registry = providers.Singleton(
        LocalAgentRegistry.from_local_yaml,
        data={
            Key(use_case="chat", type="react"): ReActAgent,
            Key(use_case="generate_description", type="base"): GenerateDescriptionAgent,
        },
    )
