from unittest.mock import AsyncMock, Mock, call

import pytest
from langchain_core.runnables import Runnable
from starlette_context import context, request_cycle_context

from ai_gateway.auth import GitLabUser, UserClaims
from ai_gateway.chat import GLAgentRemoteExecutor, TypeAgentFactory
from ai_gateway.chat.agents import (
    AgentFinalAnswer,
    AgentToolAction,
    Message,
    ReActAgentInputs,
)
from ai_gateway.chat.toolset import DuoChatToolsRegistry
from ai_gateway.internal_events import InternalEventsClient
from ai_gateway.models.base_chat import Role


@pytest.fixture()
def agent_events():
    return [AgentToolAction(thought="thought", tool="tool", tool_input="tool_input")]


@pytest.fixture()
def agent(agent_events):
    async def _stream_agent(*_args, **_kwargs):
        for action in agent_events:
            yield action

    agent = Mock(spec=Runnable)
    agent.ainvoke = AsyncMock(side_effect=lambda *_args, **_kwargs: agent_events)
    agent.astream = Mock(side_effect=_stream_agent)

    return agent


@pytest.fixture()
def agent_factory(agent):
    agent_factory = Mock(
        spec=TypeAgentFactory, side_effect=lambda *_args, **_kwargs: agent
    )

    return agent_factory


@pytest.fixture()
def tools_registry():
    return DuoChatToolsRegistry()


@pytest.fixture()
def internal_event_client():
    internal_event_client = Mock(spec=InternalEventsClient)
    return internal_event_client


@pytest.mark.parametrize(
    ("inputs", "user"),
    [
        (
            ReActAgentInputs(
                question="debug question",
                chat_history="debug chat_history",
                agent_scratchpad=[],
            ),
            GitLabUser(
                authenticated=True,
                is_debug=True,
                claims=UserClaims(scopes=["ask_issue"]),
            ),
        ),
        (
            ReActAgentInputs(
                question="question",
                chat_history="chat_history",
                agent_scratchpad=[],
            ),
            GitLabUser(
                authenticated=True,
                is_debug=False,
                claims=UserClaims(scopes=["ask_issue"]),
            ),
        ),
    ],
)
class TestGLAgentRemoteExecutor:
    @pytest.mark.asyncio
    async def test_invoke(
        self,
        agent: Mock,
        agent_factory: Mock,
        agent_events,
        tools_registry: DuoChatToolsRegistry,
        internal_event_client: Mock,
        inputs: ReActAgentInputs,
        user: GitLabUser,
    ):
        executor = GLAgentRemoteExecutor(
            agent_factory=agent_factory,
            tools_registry=tools_registry,
            internal_event_client=internal_event_client,
        )

        gl_version = "17.2.0"
        executor.on_behalf(user, gl_version)

        actual_action = await executor.invoke(inputs=inputs)

        agent_factory.assert_called_once_with(
            chat_history=inputs.chat_history,
            model_metadata=inputs.model_metadata,
            agent_inputs=inputs,
        )
        agent.ainvoke.assert_called_once_with(inputs)
        assert actual_action == agent_events

    @pytest.mark.asyncio
    async def test_stream(
        self,
        agent: Mock,
        agent_factory: Mock,
        agent_events,
        tools_registry: DuoChatToolsRegistry,
        internal_event_client: Mock,
        inputs: ReActAgentInputs,
        user: GitLabUser,
    ):
        executor = GLAgentRemoteExecutor(
            agent_factory=agent_factory,
            tools_registry=tools_registry,
            internal_event_client=internal_event_client,
        )

        gl_version = "17.2.0"
        executor.on_behalf(user, gl_version)

        with request_cycle_context({}):
            actual_actions = [action async for action in executor.stream(inputs=inputs)]

            if user.is_debug:
                assert (
                    context.get("duo_chat.agent_available_tools")
                    == "ci_editor_assistant,gitlab_documentation,epic_reader,issue_reader,merge_request_reader"
                )
            else:
                assert context.get("duo_chat.agent_available_tools") == "issue_reader"

        agent_factory.assert_called_once_with(
            chat_history=inputs.chat_history,
            model_metadata=inputs.model_metadata,
            agent_inputs=inputs,
        )
        agent.astream.assert_called_once_with(inputs)
        assert actual_actions == agent_events


class TestGLAgentRemoteExecutorToolAction:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        (
            "user",
            "gl_version",
            "inputs",
            "agent_events",
            "expected_available_tools",
            "expected_internal_events",
        ),
        [
            (
                GitLabUser(
                    authenticated=True,
                    claims=UserClaims(scopes=["duo_chat"]),
                ),
                "17.2.0",
                ReActAgentInputs(messages=[Message(role=Role.USER, content="Hi")]),
                [
                    AgentToolAction(
                        thought="", tool="ci_editor_assistant", tool_input=""
                    )
                ],
                "ci_editor_assistant",
                [call("request_duo_chat", category="ai_gateway.chat.executor")],
            ),
            (
                GitLabUser(
                    authenticated=True,
                    claims=UserClaims(scopes=["ask_issue"]),
                ),
                "17.2.0",
                ReActAgentInputs(messages=[Message(role=Role.USER, content="Hi")]),
                [AgentToolAction(thought="", tool="issue_reader", tool_input="")],
                "issue_reader",
                [call("request_ask_issue", category="ai_gateway.chat.executor")],
            ),
            (
                GitLabUser(
                    authenticated=True,
                    claims=UserClaims(scopes=["ask_epic"]),
                ),
                "17.2.0",
                ReActAgentInputs(messages=[Message(role=Role.USER, content="Hi")]),
                [AgentToolAction(thought="", tool="epic_reader", tool_input="")],
                "epic_reader",
                [call("request_ask_epic", category="ai_gateway.chat.executor")],
            ),
            (
                GitLabUser(
                    authenticated=True,
                    claims=UserClaims(scopes=["documentation_search"]),
                ),
                "17.2.0",
                ReActAgentInputs(messages=[Message(role=Role.USER, content="Hi")]),
                [
                    AgentToolAction(
                        thought="", tool="gitlab_documentation", tool_input=""
                    )
                ],
                "gitlab_documentation",
                [
                    call(
                        "request_documentation_search",
                        category="ai_gateway.chat.executor",
                    )
                ],
            ),
            (
                GitLabUser(
                    authenticated=True,
                    claims=UserClaims(scopes=["documentation_search"]),
                ),
                "17.2.0",
                ReActAgentInputs(messages=[Message(role=Role.USER, content="Hi")]),
                [
                    AgentToolAction(
                        thought="", tool="GitlabDocumentationTool", tool_input=""
                    )
                ],
                "gitlab_documentation",
                [],
            ),
            (
                GitLabUser(
                    authenticated=True,
                    claims=UserClaims(scopes=["documentation_search"]),
                ),
                "17.2.0",
                ReActAgentInputs(messages=[Message(role=Role.USER, content="Hi")]),
                [AgentToolAction(thought="", tool="", tool_input="")],
                "gitlab_documentation",
                [],
            ),
            (
                GitLabUser(
                    authenticated=True,
                    claims=UserClaims(scopes=["documentation_search"]),
                ),
                "17.2.0",
                ReActAgentInputs(messages=[Message(role=Role.USER, content="Hi")]),
                [AgentFinalAnswer(text="I'm good")],
                "gitlab_documentation",
                [],
            ),
        ],
    )
    async def test_stream_tool_action(
        self,
        agent: Mock,
        agent_factory: Mock,
        tools_registry: DuoChatToolsRegistry,
        internal_event_client: Mock,
        inputs: ReActAgentInputs,
        user: GitLabUser,
        gl_version: str,
        expected_available_tools,
        expected_internal_events,
    ):
        executor = GLAgentRemoteExecutor(
            agent_factory=agent_factory,
            tools_registry=tools_registry,
            internal_event_client=internal_event_client,
        )

        executor.on_behalf(user, gl_version)

        with request_cycle_context({}):
            async for _ in executor.stream(inputs=inputs):
                pass

            assert (
                context.get("duo_chat.agent_available_tools")
                == expected_available_tools
            )

        internal_event_client.track_event.assert_has_calls(expected_internal_events)
