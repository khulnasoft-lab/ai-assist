from unittest.mock import AsyncMock, Mock, call

import pytest
from langchain_core.runnables import Runnable
from starlette_context import request_cycle_context

from ai_gateway.chat import GLAgentRemoteExecutor
from ai_gateway.chat.agents import (
    AgentError,
    AgentFinalAnswer,
    AgentToolAction,
    Message,
    ReActAgentInputs,
)
from ai_gateway.chat.tools.base import BaseTool
from ai_gateway.chat.tools.gitlab import EpicReader, GitlabDocumentation, IssueReader
from ai_gateway.models.base_chat import Role


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
def executor(agent: Mock, tools: list[BaseTool], internal_event_client: Mock):
    yield GLAgentRemoteExecutor(
        agent=agent,
        tools=tools,
        internal_event_client=internal_event_client,
    )


@pytest.mark.parametrize(
    ("tools", "agent_events", "expected_actions", "expected_internal_events"),
    [
        (
            [IssueReader()],
            [AgentToolAction(thought="", tool="issue_reader", tool_input="")],
            [AgentToolAction(thought="", tool="issue_reader", tool_input="")],
            [call("request_ask_issue", category="ai_gateway.chat.executor")],
        ),
        (
            [EpicReader()],
            [AgentToolAction(thought="", tool="epic_reader", tool_input="")],
            [AgentToolAction(thought="", tool="epic_reader", tool_input="")],
            [call("request_ask_epic", category="ai_gateway.chat.executor")],
        ),
        (
            [GitlabDocumentation()],
            [AgentToolAction(thought="", tool="gitlab_documentation", tool_input="")],
            [AgentToolAction(thought="", tool="gitlab_documentation", tool_input="")],
            [
                call(
                    "request_documentation_search",
                    category="ai_gateway.chat.executor",
                )
            ],
        ),
        (
            [GitlabDocumentation()],
            [
                AgentToolAction(
                    thought="", tool="GitlabDocumentationTool", tool_input=""
                )
            ],
            [AgentError(type="error", message="tool not available", retryable=False)],
            [],
        ),
        (
            [GitlabDocumentation()],
            [AgentToolAction(thought="", tool="", tool_input="")],
            [AgentError(type="error", message="tool not available", retryable=False)],
            [],
        ),
        (
            [GitlabDocumentation()],
            [AgentToolAction(thought="", tool="issue_reader", tool_input="")],
            [AgentError(type="error", message="tool not available", retryable=False)],
            [],
        ),
        (
            [GitlabDocumentation()],
            [AgentFinalAnswer(text="I'm good")],
            [AgentFinalAnswer(text="I'm good")],
            [],
        ),
        (
            [],
            [],
            [],
            [],
        ),
    ],
)
class TestGLAgentRemoteExecutor:
    @pytest.mark.asyncio
    async def test_stream(
        self,
        agent: Mock,
        executor: GLAgentRemoteExecutor,
        expected_actions,
        expected_internal_events,
        internal_event_client: Mock,
    ):
        inputs = ReActAgentInputs(messages=[Message(role=Role.USER, content="Hi")])

        with request_cycle_context({}):
            actual_actions = [action async for action in executor.stream(inputs=inputs)]

        agent.astream.assert_called_once_with(inputs)
        assert actual_actions == expected_actions

        internal_event_client.track_event.assert_has_calls(expected_internal_events)


class TestGLAgentRemoteExecutorToolValidation:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("tools", "agent_events", "expected_event"),
        [
            (
                [IssueReader()],
                [AgentToolAction(thought="", tool="issue_reader", tool_input="")],
                AgentToolAction(thought="", tool="issue_reader", tool_input=""),
            ),
            (
                [EpicReader()],
                [AgentToolAction(thought="", tool="issue_reader", tool_input="")],
                AgentError(message="tool not available", retryable=False),
            ),
            (
                [IssueReader()],
                [AgentToolAction(thought="", tool="IssueReader", tool_input="")],
                AgentError(message="tool not available", retryable=False),
            ),
        ],
    )
    async def test_stream_tool_validation(
        self,
        executor: GLAgentRemoteExecutor,
        expected_event,
    ):

        inputs = ReActAgentInputs(messages=[Message(role=Role.USER, content="Hi")])

        with request_cycle_context({}):
            async for event in executor.stream(inputs=inputs):
                assert event == expected_event
