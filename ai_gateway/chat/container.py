from typing import TYPE_CHECKING

from dependency_injector import containers, providers

from ai_gateway.chat.executor import GLAgentRemoteExecutor
from ai_gateway.chat.toolset import DuoChatToolsRegistry

if TYPE_CHECKING:
    from ai_gateway.api.auth_utils import StarletteUser
    from ai_gateway.internal_events.client import InternalEventsClient
    from ai_gateway.models.base import ModelMetadata
    from ai_gateway.prompts import BasePromptRegistry

__all__ = [
    "ContainerChat",
]


def _gl_agent_remote_executor_factory(
    prompt_registry: "BasePromptRegistry",
    tools_registry: DuoChatToolsRegistry,
    internal_event_client: "InternalEventsClient",
    user: "StarletteUser",
    model_metadata: "ModelMetadata | None",
    gl_version: str,
    **kwargs
) -> GLAgentRemoteExecutor:
    agent = prompt_registry.get_on_behalf(user, "chat/react", model_metadata, **kwargs)

    if user.is_debug:
        tools = tools_registry.get_all()
    else:
        tools = tools_registry.get_on_behalf(user, gl_version)

    return GLAgentRemoteExecutor(
        agent=agent, tools=tools, internal_event_client=internal_event_client
    )


class ContainerChat(containers.DeclarativeContainer):
    prompts = providers.DependenciesContainer()
    models = providers.DependenciesContainer()
    internal_event = providers.DependenciesContainer()
    config = providers.Configuration(strict=True)

    # The dependency injector does not allow us to override the FactoryAggregate provider directly.
    # However, we can still override its internal sub-factories to achieve the same goal.
    _anthropic_claude_llm_factory = providers.Factory(models.anthropic_claude)
    _anthropic_claude_chat_factory = providers.Factory(models.anthropic_claude_chat)

    # We need to resolve the model based on model name provided in request payload
    # Hence, `models._anthropic_claude` and `models._anthropic_claude_chat_factory` are only partially applied here.
    anthropic_claude_factory = providers.FactoryAggregate(
        llm=_anthropic_claude_llm_factory, chat=_anthropic_claude_chat_factory
    )

    litellm_factory = providers.Factory(models.litellm_chat)

    _tools_registry = providers.Factory(
        DuoChatToolsRegistry,
        self_hosted_documentation_enabled=config.custom_models.enabled,
    )

    gl_agent_remote_executor = providers.Factory(
        _gl_agent_remote_executor_factory,
        prompt_registry=prompts.prompt_registry,
        tools_registry=_tools_registry,
        internal_event_client=internal_event.client,
    )
