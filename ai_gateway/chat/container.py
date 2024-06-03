from typing import Sequence

from dependency_injector import containers, providers

from ai_gateway.agents import BaseAgentRegistry
from ai_gateway.agents.chat import ReActAgent, ReActAgentInputs, TypeReActAgentAction
from ai_gateway.chat.executor import GLAgentRemoteExecutor, TypeAgentFactory
from ai_gateway.chat.tools import BaseTool
from ai_gateway.chat.tools.gitlab import GitLabToolkit

__all__ = [
    "ContainerChat",
]


def _react_agent_factory(
    agent_registry: BaseAgentRegistry,
) -> TypeAgentFactory[ReActAgentInputs, TypeReActAgentAction]:
    def _fn(tools: Sequence[BaseTool], inputs: ReActAgentInputs) -> ReActAgent:
        options = {}
        if context := inputs.context:
            options.update(
                {"context_type": context.type, "context_content": context.content}
            )

        return agent_registry.get("chat", "react", options)

    return _fn


class ContainerChat(containers.DeclarativeContainer):
    agents = providers.DependenciesContainer()
    models = providers.DependenciesContainer()

    # The dependency injector does not allow us to override the FactoryAggregate provider directly.
    # However, we can still override its internal sub-factories to achieve the same goal.
    _anthropic_claude_llm_factory = providers.Factory(models.anthropic_claude)
    _anthropic_claude_chat_factory = providers.Factory(models.anthropic_claude_chat)

    _react_agent_factory = providers.Factory(
        _react_agent_factory,
        agent_registry=agents.agent_registry,
    )

    # We need to resolve the model based on model name provided in request payload
    # Hence, `models._anthropic_claude` and `models._anthropic_claude_chat_factory` are only partially applied here.
    anthropic_claude_factory = providers.FactoryAggregate(
        llm=_anthropic_claude_llm_factory, chat=_anthropic_claude_chat_factory
    )

    litellm_factory = providers.Factory(models.litellm)

    gl_agent_remote_executor = providers.Factory(
        GLAgentRemoteExecutor,
        agent_factory=_react_agent_factory,
        tools=GitLabToolkit().get_tools(),
    )
