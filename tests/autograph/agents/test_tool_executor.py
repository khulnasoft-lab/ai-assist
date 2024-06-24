from unittest.mock import MagicMock, patch

import pytest
from langchain.tools import Tool
from langgraph.prebuilt import ToolNode

from autograph.agents import ToolExecutor
from autograph.entities.state import WorkflowState


@pytest.mark.asyncio
async def test_tool_executor_run():
    mock_tool = Tool(name="test_tool", description="A test tool", func=lambda x: x)
    tool_node_mock = MagicMock(ToolNode)

    with patch(
        "autograph.agents.tool_executor.ToolNode",
        MagicMock(return_value=tool_node_mock),
    ) as tool_node_mock_class:
        tool_executor = ToolExecutor([mock_tool])
        mock_state = WorkflowState({"messages": ["tool_message"]})
        tool_node_mock.ainvoke.return_value = {"messages": ["test_tool output"]}

        output = await tool_executor.run(mock_state)

        tool_node_mock_class.assert_called_once_with([mock_tool])
        tool_node_mock.ainvoke.assert_called_once_with(mock_state)

        assert output == {"messages": ["tool_message", "test_tool output"]}
