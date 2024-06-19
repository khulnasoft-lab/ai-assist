from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field, PrivateAttr

from autograph.entities import AgentConfig, WorkflowState

__all__ = ["HandoverTool", "HandoverAgent"]


class HandoverTool(BaseModel):
    description: str = """A final response to the user"""
    summary: str = Field(
        description="The summary of the work done based on the past conversation between human, agent and tools executions"
    )


class HandoverAgent(BaseModel):
    """Agent that summarizes the workflow"""

    config: AgentConfig
    _llm: Runnable = PrivateAttr()

    def __init__(self, config: AgentConfig):
        super().__init__(config=config)
        llm = ChatAnthropic(model_name=config.model, temperature=config.temperature)  # type: ignore
        system_prompt = """
        You are an expert manager, your task is to assure smoth work hand over between multiple team memebrs.
        You complete your task by reviwing past conversation between team memebrs and summarising the progress that has been achieved towards the goal.
        You should include information what has been delivered, what is missing, and what problems had been encountered
    """
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "The goal is: {goal}"),
                ("human", "The conversation to summarize: {messages}"),
            ]
        )
        self._llm = prompt_template | llm

    def run(self, state: WorkflowState):
        response = self._llm.invoke(
            {"goal": state["goal"], "messages": state["messages"]}
        )
        return {"previous_step_summary": response.content, "plan": [], "messages": []}
