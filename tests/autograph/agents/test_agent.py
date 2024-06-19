from unittest.mock import MagicMock, patch

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from autograph.agents import Agent
from autograph.entities import Cost, WorkflowState


class TestAgent:
    def test_setup(self, agent_config, tools):
        agent = Agent(config=agent_config)
        chat_anthropic_mock = MagicMock(ChatAnthropic)
        chat_anthropic_class_mock = MagicMock(return_value=chat_anthropic_mock)
        chat_anthropic_mock.bind_tools.return_value = "Set up model"
        with patch("autograph.agents.agent.ChatAnthropic", chat_anthropic_class_mock):
            agent.setup(tools)

            chat_anthropic_class_mock.assert_called_once_with(
                model_name=agent_config.model, temperature=agent_config.temperature
            )
            chat_anthropic_mock.bind_tools.assert_called_once_with(tools)

            assert agent._llm == "Set up model"

    @pytest.mark.parametrize(
        ("previous_conversation", "messages_passed_to_model"),
        [
            (
                [SystemMessage(content="Some previous conversation.")],
                [SystemMessage(content="Some previous conversation.")],
            ),
            (
                [],
                [
                    SystemMessage(content="You are a helpful assistant."),
                    HumanMessage(
                        content="Overall Goal: Test goal\nYour Goal: Provide a helpful response."
                    ),
                ],
            ),
        ],
    )
    def test_run(
        self, agent_config, tools, previous_conversation, messages_passed_to_model
    ):
        agent = Agent(config=agent_config)
        model_response = AIMessage(
            content="Test response",
            response_metadata={
                "usage": {"total_tokens": 5, "input_tokens": 2, "output_tokens": 3}
            },
        )

        chat_anthropic_mock = MagicMock(ChatAnthropic)
        chat_anthropic_mock.reset_mock()
        with patch("autograph.agents.agent.time.time", return_value=123456789), patch(
            "autograph.agents.agent.ChatAnthropic",
            MagicMock(return_value=chat_anthropic_mock),
        ):
            chat_anthropic_mock.bind_tools.return_value = chat_anthropic_mock
            chat_anthropic_mock.invoke.return_value = model_response

            state = WorkflowState(
                goal="Test goal",
                messages=previous_conversation,
            )

            agent.setup(tools)
            result = agent.run(state)

            chat_anthropic_mock.invoke.assert_called_once_with(messages_passed_to_model)
            assert result["messages"] == messages_passed_to_model + [model_response]
            assert result["actions"] == [
                {
                    "actor": agent_config.name,
                    "contents": "Test response",
                    "time": 123456789,
                }
            ]
            assert result["costs"] == (
                agent_config.model,
                Cost(llm_calls=1, input_tokens=2, output_tokens=3),
            )

    def test_run_raises_error_when_agent_not_setup(self, agent_config):
        agent = Agent(config=agent_config)
        state = WorkflowState(
            goal="Test goal",
            messages=[],
        )
        with pytest.raises(
            ValueError, match=r"Agent not setup\. Please call setup\(\) first\."
        ):
            agent.run(state)
