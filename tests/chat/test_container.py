from typing import Type, cast
from unittest.mock import Mock, patch

import pytest
from dependency_injector import containers, providers

from ai_gateway import Config
from ai_gateway.api.auth_utils import StarletteUser
from ai_gateway.chat.agents.typing import Message
from ai_gateway.chat.executor import GLAgentRemoteExecutor
from ai_gateway.chat.tools import BaseTool
from ai_gateway.chat.tools.gitlab import (
    BuildReader,
    EpicReader,
    GitlabDocumentation,
    IssueReader,
    MergeRequestReader,
    SelfHostedGitlabDocumentation,
)
from ai_gateway.models.anthropic import (
    AnthropicChatModel,
    AnthropicModel,
    KindAnthropicModel,
)
from ai_gateway.models.base_chat import Role
from ai_gateway.models.litellm import KindLiteLlmModel, LiteLlmChatModel
from ai_gateway.prompts.typing import ModelMetadata


@pytest.fixture
def mock_config(custom_models_enabled: bool):
    config = Config()
    config.custom_models.enabled = custom_models_enabled

    yield config


@pytest.fixture
def messages():
    yield [Message(role=Role.USER, content="")]


@pytest.fixture
def scopes():
    yield ["duo_chat", "documentation_search"]


@pytest.fixture
def mock_registry_get_on_behalf():
    with patch("ai_gateway.prompts.registry.BasePromptRegistry.get_on_behalf") as mock:
        yield mock


@pytest.mark.parametrize("custom_models_enabled", [False])
def test_container(
    mock_container: containers.DeclarativeContainer,
    model_metadata: ModelMetadata,
    user: StarletteUser,
    messages: list[Message],
):
    chat = cast(providers.Container, mock_container.chat)

    assert isinstance(
        chat.anthropic_claude_factory("llm", name=KindAnthropicModel.CLAUDE_2_0),
        AnthropicModel,
    )
    assert isinstance(
        chat.anthropic_claude_factory("chat", name=KindAnthropicModel.CLAUDE_2_0),
        AnthropicChatModel,
    )
    assert isinstance(
        chat.litellm_factory(name=KindLiteLlmModel.MISTRAL), LiteLlmChatModel
    )
    assert isinstance(
        chat.gl_agent_remote_executor(
            user=user, gl_version="", model_metadata=model_metadata, messages=messages
        ),
        GLAgentRemoteExecutor,
    )


@pytest.mark.parametrize(
    ("user_is_debug", "custom_models_enabled", "expected_tool_types"),
    [
        (
            True,
            True,
            [
                BuildReader,
                SelfHostedGitlabDocumentation,
                EpicReader,
                IssueReader,
                MergeRequestReader,
            ],
        ),
        (
            True,
            False,
            [
                BuildReader,
                GitlabDocumentation,
                EpicReader,
                IssueReader,
                MergeRequestReader,
            ],
        ),
        (
            False,
            True,
            [SelfHostedGitlabDocumentation],
        ),
        (
            False,
            False,
            [GitlabDocumentation],
        ),
    ],
)
def test_container_with_config(
    mock_container: containers.DeclarativeContainer,
    mock_registry_get_on_behalf: Mock,
    model_metadata: ModelMetadata,
    messages: list[Message],
    user: StarletteUser,
    user_is_debug: bool,
    custom_models_enabled: bool,
    expected_tool_types: Type[BaseTool],
):
    chat = cast(providers.Container, mock_container.chat)
    remote_executor = chat.gl_agent_remote_executor(
        user=user, gl_version="", model_metadata=model_metadata, messages=messages
    )

    mock_registry_get_on_behalf.assert_called_once_with(
        user, "chat/react", model_metadata, messages=messages
    )

    tool_types = {type(tool) for tool in remote_executor.tools}

    assert set(expected_tool_types) == tool_types
