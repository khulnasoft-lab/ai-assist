from typing import List

from langchain.tools import Tool
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, PrivateAttr

from autograph.entities import (
    AgentConfig,
    Cost,
    Plan,
    Task,
    TaskStatusEnum,
    TaskStatusInput,
    WorkflowState,
)

__all__ = ["PlannerAgent", "PlanSupervisorAgent"]


class PlannerAgent(BaseModel):
    """Agent that plans the workflow"""

    config: AgentConfig
    _llm: Runnable = PrivateAttr()
    _input_messages: List[BaseMessage] = PrivateAttr()

    def __init__(self, config: AgentConfig, team: List[AgentConfig], tools: List[Tool]):
        super().__init__(config=config)
        schema = Plan.model_json_schema()
        llm = ChatAnthropic(
            model_name=config.model, temperature=config.temperature
        )  # type: ignore
        self._llm = llm.with_structured_output(schema, include_raw=True)
        self._system_prompt = f"""
        For the given goal, come up with a simple step by step plan that can be deliver by the team appointed by user.
        Only inlcude steps that can be deliverd by the assinged team with the assigned tools,\
        when some additional steps smees to be required assume that they will be done afterwards by the user.  \
        This plan should involve individual tasks, that if executed correctly will yield the correct answer.\
        Do not add any superfluous steps. \
        The result of the final step should be the call to HandoverTool.

        You must respond with entity that match following JSONSchema
        ```schema
        {schema}
        ```
        """
        self._input_messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(
                content=f"The team consist of: {[agent_config.system_prompt for agent_config in team]}"
            ),
            HumanMessage(
                content=f"The team has access to following tools: {[tool.description for tool in tools]}"
            ),
        ]

    def run(self, state: WorkflowState):
        resp = self._llm.invoke(
            self._input_messages
            + [HumanMessage(content=f"The goal is: {state['goal']}")]
        )
        usage_data = resp["raw"].response_metadata["usage"]
        return {
            "plan": [Task(**task) for task in resp["parsed"]["steps"]],
            "costs": (
                self.config.model,
                Cost(
                    llm_calls=1,
                    input_tokens=usage_data["input_tokens"],
                    output_tokens=usage_data["output_tokens"],
                ),
            ),
        }


class PlanSupervisorAgent(BaseModel):
    """Agent that supervises the plan"""

    config: AgentConfig
    _llm: Runnable = PrivateAttr()
    _prompt_template: ChatPromptTemplate = PrivateAttr()

    def __init__(self, config: AgentConfig):
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
        super().__init__(
            config=AgentConfig(
                goal=config.goal,
                name="plan supervisor",
                model=config.model,
                temperature=config.temperature,
                system_prompt=system_prompt,
                tools=config.tools,
            )
        )

        llm = ChatAnthropic(model_name=config.model, temperature=config.temperature)  # type: ignore

        self._prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", self.config.system_prompt),
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
        self._llm = llm.with_structured_output(TaskStatusInput, include_raw=True)  # type: ignore[arg-type]

    def run(self, state: WorkflowState):
        messages = list(state["messages"])
        revised_plan = [
            self._revise_task(task, state["goal"], messages) for task in state["plan"]
        ]

        open_tasks = [
            task
            for task in revised_plan
            if task.status not in (TaskStatusEnum.CANCELLED, TaskStatusEnum.COMPLETED)
        ]
        messages.append(
            HumanMessage(
                content=f"I've revised the plan, the current status is: {revised_plan}"
            )
        )

        if len(open_tasks) > 0:
            messages.append(
                HumanMessage(content=f"Next task to implement is: {open_tasks[0]}")
            )
        else:
            messages.append(
                HumanMessage(
                    content="All taksk were completed please call HandoverTool tool"
                )
            )

        return {"plan": revised_plan, "messages": messages}

    def _revise_task(self, task: Task, goal: str, messages: List[BaseMessage]) -> Task:
        if task.status in (TaskStatusEnum.CANCELLED, TaskStatusEnum.COMPLETED):
            return task

        input_messages = self._prompt_template.format(
            goal=goal,
            task=task,
            status=task.status,
            messages=messages,
        )

        output = self._llm.invoke(input_messages)

        new_satus = output.get("parsed")

        if not new_satus:
            # LLM output failed to parse into desired output
            return task

        return Task(description=task.description, status=new_satus["status"])
