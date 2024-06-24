from typing import List

from langchain.tools import Tool
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, PrivateAttr

from autograph.entities.state import WorkflowState


class ToolExecutor(BaseModel):
    _tool_node: ToolNode = PrivateAttr()

    def __init__(self, tools: List[Tool]):
        super().__init__()
        self._tool_node = ToolNode(tools)

    # extract messages to align output with non mutable messages key in state
    # each node that whishes to modify messages history, needs to rewrite it
    async def run(self, state: WorkflowState):
        response = await self._tool_node.ainvoke(state)
        return {"messages": state["messages"] + response["messages"]}
