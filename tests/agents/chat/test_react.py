from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
)
from langchain_core.prompts import ChatPromptTemplate

from ai_gateway.agents.chat.react import (
    ReActAgent,
    ReActAgentFinalAnswer,
    ReActAgentInputs,
    ReActAgentMessage,
    ReActAgentToolAction,
    ReActPlainTextParser,
    TypeReActAgentAction,
    agent_scratchpad_plain_text_renderer,
    chat_history_plain_text_renderer,
)
from ai_gateway.agents.chat.typing import AgentStep


@pytest.fixture
def prompt_template() -> ChatPromptTemplate:

    return ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content="{chat_history} "
                " You are a DevSecOps Assistant named 'GitLab Duo Chat' created by GitLab."
            ),
            HumanMessage(content="{question}"),
            AIMessage(content="{agent_scratchpad}"),
        ]
    )


@pytest.mark.parametrize(
    ("chat_history", "expected"),
    [
        (["str1", "str2"], "str1\nstr2"),
        ("str1\nstr2", "str1\nstr2"),
    ],
)
def test_chat_history_plain_text_renderer(chat_history: str | list[str], expected: str):
    actual = chat_history_plain_text_renderer(chat_history)
    assert actual == expected


@pytest.mark.parametrize(
    ("scratchpad", "expected"),
    [
        (
            [
                AgentStep(
                    action=ReActAgentToolAction(
                        tool="tool1", tool_input="tool_input1", thought="thought1"
                    ),
                    observation="observation1",
                ),
                AgentStep(
                    action=ReActAgentToolAction(
                        tool="tool2", tool_input="tool_input2", thought="thought2"
                    ),
                    observation="observation2",
                ),
                AgentStep(
                    action=ReActAgentFinalAnswer(
                        text="final_answer", thought="thought3"
                    ),
                    observation="observation3",
                ),
            ],
            (
                "Thought: thought1\n"
                "Action: tool1\n"
                "Action Input: tool_input1\n"
                "Observation: observation1\n"
                "Thought: thought2\n"
                "Action: tool2\n"
                "Action Input: tool_input2\n"
                "Observation: observation2"
            ),
        )
    ],
)
def test_agent_scratchpad_plain_text_renderer(
    scratchpad: list[AgentStep], expected: str
):
    actual = agent_scratchpad_plain_text_renderer(scratchpad)

    assert actual == expected


class TestReActPlainTextParser:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            (
                "thought1\nAction: tool1\nAction Input: tool_input1\n",
                ReActAgentToolAction(
                    thought="thought1",
                    log="Thought: thought1\nAction: tool1\nAction Input: tool_input1",
                    tool="tool1",
                    tool_input="tool_input1",
                ),
            ),
            (
                "thought1\nFinal Answer: final answer\n",
                ReActAgentFinalAnswer(
                    thought="thought1",
                    log="Thought: thought1\nFinal Answer: final answer",
                    text="final answer",
                ),
            ),
        ],
    )
    def test_agent_message(self, text: str, expected: ReActAgentMessage):
        parser = ReActPlainTextParser()
        actual = parser.parse(text)

        assert actual == expected

    @pytest.mark.parametrize("text", ["random_text"])
    def test_error(self, text: str):
        parser = ReActPlainTextParser()

        with pytest.raises(ValueError):
            parser.parse(text)


class TestReActAgent:
    @pytest.mark.asyncio
    @patch("langchain_core.language_models.chat_models.BaseChatModel.ainvoke")
    @pytest.mark.parametrize(
        (
            "question",
            "chat_history",
            "agent_scratchpad",
            "expected_action",
        ),
        [
            (
                "What's the title of this epic?",
                "",
                [],
                ReActAgentToolAction(
                    thought="I'm thinking...",
                    tool="ci_issue_reader",
                    tool_input="random input",
                    log="Thought: I'm thinking...\nAction: ci_issue_reader\nAction Input: random input",
                ),
            ),
            (
                "What's the title of this issue?",
                ["User: what's the description of this issue", "AI: PoC ReAct"],
                [],
                ReActAgentToolAction(
                    thought="I'm thinking...",
                    tool="ci_issue_reader",
                    tool_input="random input",
                    log="Thought: I'm thinking...\nAction: ci_issue_reader\nAction Input: random input",
                ),
            ),
            (
                "What's the title of this issue?",
                ["User: what's the description of this issue", "AI: PoC ReAct"],
                [],
                ReActAgentToolAction(
                    thought="I'm thinking...",
                    tool="ci_issue_reader",
                    tool_input="random input",
                    log="Thought: I'm thinking...\nAction: ci_issue_reader\nAction Input: random input",
                ),
            ),
            (
                "What's your name?",
                "User: what's the description of this issue\nAI: PoC ReAct",
                [
                    AgentStep[TypeReActAgentAction](
                        action=ReActAgentToolAction(
                            thought="thought",
                            tool="ci_issue_reader",
                            tool_input="random input",
                        ),
                        observation="observation",
                    )
                ],
                ReActAgentFinalAnswer(
                    thought="I'm thinking...",
                    text="Paris",
                    log="Thought: I'm thinking...\nFinal Answer: Paris",
                ),
            ),
        ],
    )
    async def test_invoke(
        self,
        mock_ainvoke: Mock,
        prompt_template: ChatPromptTemplate,
        question: str,
        chat_history: list[str] | str,
        agent_scratchpad: list[AgentStep],
        expected_action: TypeReActAgentAction,
    ):
        def _model_invoke(*args, **kwargs):
            text = expected_action.log[
                len("Thought: ") :
            ]  # our default Assistant prompt template already contains "Thought: "
            return AIMessage(text)

        mock_ainvoke.side_effect = _model_invoke

        model = ChatAnthropic(
            model="claude-3-sonnet-20240229"
        )  # type: ignore[call-arg]

        inputs = ReActAgentInputs(
            question=question,
            chat_history=chat_history,
            agent_scratchpad=agent_scratchpad,
        )

        agent = ReActAgent.from_model(
            name="test", model=model, prompt_template=prompt_template
        )
        actual_action = await agent.ainvoke(inputs)

        assert actual_action == expected_action

    @pytest.mark.asyncio
    @patch("langchain_core.language_models.chat_models.BaseChatModel.astream")
    @pytest.mark.parametrize(
        (
            "question",
            "chat_history",
            "agent_scratchpad",
            "model_response",
            "expected_actions",
        ),
        [
            (
                "What's the title of this epic?",
                "",
                [],
                "Thought: I'm thinking...\nAction: ci_issue_reader\nAction Input: random input",
                [
                    ReActAgentToolAction(
                        thought="I'm thinking...",
                        log="Thought: I'm thinking...\nAction: ci_issue_reader\nAction Input: random input",
                        tool="ci_issue_reader",
                        tool_input="random input",
                    ),
                ],
            ),
            (
                "What's your name?",
                "User: what's the description of this issue\nAI: PoC ReAct",
                [
                    AgentStep[TypeReActAgentAction](
                        action=ReActAgentToolAction(
                            thought="thought",
                            tool="ci_issue_reader",
                            tool_input="random input",
                        ),
                        observation="observation",
                    )
                ],
                "Thought: I'm thinking...\nFinal Answer: It's Paris",
                [
                    ReActAgentFinalAnswer(
                        thought="I'm thinking...",
                        log="Thought: I'm thinking...\nFinal Answer: It's",
                        text="It's",
                    ),
                    ReActAgentFinalAnswer(thought="", log=" Paris", text=" Paris"),
                ],
            ),
        ],
    )
    async def test_stream(
        self,
        mock_astream: AsyncMock,
        prompt_template: ChatPromptTemplate,
        question: str,
        chat_history: list[str] | str,
        agent_scratchpad: list[AgentStep],
        model_response: str,
        expected_actions: list[ReActAgentToolAction | ReActAgentFinalAnswer],
    ):
        async def _model_astream(*args, **kwargs):
            text = model_response[
                len("Thought: ") :
            ]  # our default Assistant prompt template already contains "Thought: "

            for i in range(0, len(text), 5):
                yield AIMessageChunk(content=text[i : i + 5])

        mock_astream.side_effect = _model_astream

        model = ChatAnthropic(model="claude-3-sonnet-20240229")  # type: ignore[call-arg]

        inputs = ReActAgentInputs(
            question=question,
            chat_history=chat_history,
            agent_scratchpad=agent_scratchpad,
        )

        agent = ReActAgent.from_model(
            name="test", model=model, prompt_template=prompt_template
        )

        actual_actions = [action async for action in agent.astream(inputs)]
        assert actual_actions == expected_actions
