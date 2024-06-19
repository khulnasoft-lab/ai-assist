from unittest.mock import MagicMock, call, patch

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from autograph.agents import PlannerAgent, PlanSupervisorAgent
from autograph.entities import (
    Cost,
    Plan,
    Task,
    TaskStatusEnum,
    TaskStatusInput,
    WorkflowState,
)


class TestPlannerAgent:
    def test_setup(self, agent_config, tools):
        chat_anthropic_mock = MagicMock(ChatAnthropic)
        chat_anthropic_class_mock = MagicMock(return_value=chat_anthropic_mock)
        chat_anthropic_mock.with_structured_output.return_value = "Set up model"
        with patch("autograph.agents.planing.ChatAnthropic", chat_anthropic_class_mock):
            planner_agent = PlannerAgent(
                config=agent_config, team=[agent_config], tools=tools
            )

            assert planner_agent._llm == "Set up model"
            chat_anthropic_class_mock.assert_called_once_with(
                model_name=agent_config.model, temperature=agent_config.temperature
            )
            chat_anthropic_mock.with_structured_output.assert_called_once_with(
                Plan.model_json_schema(), include_raw=True
            )

    def test_run(self, agent_config, tools):
        model_response = {
            "parsed": {
                "steps": [
                    {
                        "description": "Do something",
                        "status": TaskStatusEnum.NOT_STARTED,
                    },
                    {
                        "description": "Do something else",
                        "status": TaskStatusEnum.NOT_STARTED,
                    },
                ]
            },
            "raw": AIMessage(
                content="Test plan",
                response_metadata={
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 20,
                        "total_tokens": 30,
                    }
                },
            ),
        }

        chat_anthropic_mock = MagicMock(ChatAnthropic)
        chat_anthropic_mock.with_structured_output.return_value = chat_anthropic_mock
        chat_anthropic_mock.invoke.return_value = model_response

        with patch(
            "autograph.agents.planing.ChatAnthropic",
            MagicMock(return_value=chat_anthropic_mock),
        ):
            planner_agent = PlannerAgent(
                config=agent_config, team=[agent_config], tools=tools
            )
            state = WorkflowState(goal="Test goal")
            result = planner_agent.run(state)

            chat_anthropic_mock.invoke.assert_called_once_with(
                [
                    SystemMessage(content=planner_agent._system_prompt),
                    HumanMessage(
                        content="The team consist of: ['You are a helpful assistant.']"
                    ),
                    HumanMessage(
                        content="The team has access to following tools: ['Search the web for information', 'Perform mathematical calculations']"
                    ),
                    HumanMessage(content="The goal is: Test goal"),
                ]
            )
            assert result["plan"] == [
                Task(description="Do something", status=TaskStatusEnum.NOT_STARTED),
                Task(
                    description="Do something else", status=TaskStatusEnum.NOT_STARTED
                ),
            ]
            assert result["costs"] == (
                agent_config.model,
                Cost(llm_calls=1, input_tokens=10, output_tokens=20),
            )


class TestPlanSupervisorAgent:
    system_prompt = """
        You are an expert project manager. Your assignment is to supervise execution of
        the plan by experienced engieer.
        The plan consist of set of Tasks with their statuses.
        You are presented with one Task at the time.
        You must review all messages in the conversation documenting work done by
        the experienced engineer and mark the Task with correct status
        Tasks statuses: Not Started, In Progress, Completed, Cancelled
        Do not update task status is you are not sure which new status should be applied!
        """

    def test_setup(self, agent_config, tools):
        chat_anthropic_mock = MagicMock(ChatAnthropic)
        chat_anthropic_class_mock = MagicMock(return_value=chat_anthropic_mock)
        chat_anthropic_mock.with_structured_output.return_value = chat_anthropic_mock
        prompt_template_mock = MagicMock(ChatPromptTemplate)

        with patch(
            "autograph.agents.planing.ChatAnthropic", chat_anthropic_class_mock
        ), patch("autograph.agents.planing.ChatPromptTemplate", prompt_template_mock):
            plan_supervisor_agent = PlanSupervisorAgent(config=agent_config)

            assert plan_supervisor_agent._llm is not None
            chat_anthropic_class_mock.assert_called_once_with(
                model_name=agent_config.model, temperature=agent_config.temperature
            )
            prompt_template_mock.from_messages.assert_called_once_with(
                [
                    ("system", self.system_prompt),
                    ("human", "The goal is: {goal}"),
                    (
                        "human",
                        "The current task to review is: {task}, the task previous state is {status}",
                    ),
                    (
                        "human",
                        "Here is conversation documentig all progress made so far: {messages}",
                    ),
                    ("human", "Please assign correct status to the task: {task}"),
                ]
            )
            chat_anthropic_mock.with_structured_output.assert_called_once_with(
                TaskStatusInput, include_raw=True
            )

    def test_run(self, agent_config, tools):
        task1 = Task(description="Do something", status=TaskStatusEnum.NOT_STARTED)
        task2 = Task(description="Do something else", status=TaskStatusEnum.IN_PROGRESS)
        plan = [task1, task2]
        messages = [
            HumanMessage(content="Started working on task 1"),
            AIMessage(content="Task 1 is now in progress"),
            HumanMessage(content="Completed task 1"),
        ]
        state = WorkflowState(goal="Test goal", plan=plan, messages=messages)

        model_response = {
            "parsed": {"status": TaskStatusEnum.COMPLETED},
            "raw": AIMessage(
                content="Task 1 completed",
                response_metadata={
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 20,
                        "total_tokens": 30,
                    }
                },
            ),
        }

        chat_anthropic_mock = MagicMock(ChatAnthropic)
        chat_anthropic_mock.with_structured_output.return_value = chat_anthropic_mock
        chat_anthropic_mock.invoke.return_value = model_response
        prompt_template_mock = MagicMock(ChatPromptTemplate)

        with patch(
            "autograph.agents.planing.ChatAnthropic",
            MagicMock(return_value=chat_anthropic_mock),
        ), patch(
            "autograph.agents.planing.ChatPromptTemplate.from_messages",
            return_value=prompt_template_mock,
        ):
            formated_messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content="The goal is: Test goal"),
            ]
            prompt_template_mock.format.return_value = formated_messages

            plan_supervisor_agent = PlanSupervisorAgent(config=agent_config)
            result = plan_supervisor_agent.run(state)

            model_calls = [
                call(formated_messages),
                call(formated_messages),
            ]

            assert prompt_template_mock.format.call_count == 2
            assert chat_anthropic_mock.invoke.call_count == 2
            chat_anthropic_mock.invoke.assert_has_calls(model_calls)

            assert result["plan"] == [
                Task(description="Do something", status=TaskStatusEnum.COMPLETED),
                Task(description="Do something else", status=TaskStatusEnum.COMPLETED),
            ]
            assert result["messages"] == [
                *messages,
                HumanMessage(
                    content=f"I've revised the plan, the current status is: [Task(description='Do something', status='{TaskStatusEnum.COMPLETED}'), Task(description='Do something else', status='{TaskStatusEnum.COMPLETED}')]"
                ),
                HumanMessage(
                    content="All taksk were completed please call HandoverTool tool"
                ),
            ]
