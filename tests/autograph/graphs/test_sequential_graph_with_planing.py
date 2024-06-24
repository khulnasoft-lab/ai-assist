from unittest.mock import MagicMock, call, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph

from autograph.agents import Agent, HandoverTool
from autograph.entities import AgentConfig, WorkflowConfig, WorkflowState
from autograph.graphs.sequential_graph_with_planning import (
    SequentialGraphWithPlanningRoutes,
    _graph_with_planning_router,
    graph_with_planning,
)


@pytest.mark.parametrize(
    "state, expected",
    [
        (
            {"messages": [HumanMessage("Hello"), AIMessage("Hi")]},
            SequentialGraphWithPlanningRoutes.SUPERVISOR,
        ),
        (
            {
                "messages": [
                    HumanMessage("Hello"),
                    AIMessage(
                        "Hi", tool_calls=[{"id": 1, "args": [], "name": "HandoverTool"}]
                    ),
                ]
            },
            SequentialGraphWithPlanningRoutes.NEXT,
        ),
        (
            {
                "messages": [
                    HumanMessage("Hello"),
                    AIMessage(
                        "Hi", tool_calls=[{"id": 1, "args": [], "name": "OtherTool"}]
                    ),
                ]
            },
            SequentialGraphWithPlanningRoutes.CALL_TOOL,
        ),
    ],
)
def test_graph_with_planning_router(state, expected):
    assert _graph_with_planning_router(state) == expected


@patch("autograph.graphs.sequential_graph_with_planning.PlannerAgent")
@patch("autograph.graphs.sequential_graph_with_planning.PlanSupervisorAgent")
@patch("autograph.graphs.sequential_graph_with_planning.ToolExecutor")
@patch("autograph.graphs.sequential_graph_with_planning.HandoverAgent")
def test_graph_with_planing(
    mock_handover_agent_class,
    mock_tool_executor_class,
    mock_plan_supervisor_agent_class,
    mock_planner_agent_class,
):
    config = WorkflowConfig(
        name="test_workflow",
        example_prompt="Example prompt",
        agents=[
            AgentConfig(
                name="agent1",
                system_prompt="System prompt 1",
                model="model1",
                goal="Goal 1",
                temperature=0.7,
                tools=["tool1", "tool2"],
            ),
            AgentConfig(
                name="agent2",
                system_prompt="System prompt 2",
                model="model2",
                goal="Goal 2",
                temperature=0.8,
                tools=["tool3", "tool4"],
            ),
        ],
        workflow=["agent1", "agent2"],
    )

    mock_agents = [MagicMock(Agent) for _ in config.agents]
    mock_graph = MagicMock(StateGraph)
    with patch(
        "autograph.graphs.sequential_graph_with_planning.Agent",
        MagicMock(side_effect=mock_agents),
    ) as mock_agent_class, patch(
        "autograph.graphs.sequential_graph_with_planning.StateGraph",
        MagicMock(return_value=mock_graph),
    ) as mock_graph_class:
        mock_graph.compile.return_value = "Complied graph"

        graph = graph_with_planning(config)

        assert graph == "Complied graph"
        mock_graph_class.assert_called_once_with(WorkflowState)
        mock_agent_class.assert_has_calls(
            [
                call(config=config.agents[0]),
                call(config=config.agents[1]),
            ]
        )

        for mock_agent in mock_agents:
            mock_agent.setup.assert_called_with([HandoverTool])

        mock_planner_agent_class.assert_has_calls(
            [
                call(config=config.agents[0], team=[config.agents[0]], tools=[]),
                call(config=config.agents[1], team=[config.agents[1]], tools=[]),
            ]
        )

        mock_plan_supervisor_agent_class.assert_has_calls(
            [call(config.agents[0]), call(config.agents[1])]
        )

        mock_tool_executor_class.assert_has_calls([call([]), call([])])

        mock_handover_agent_class.assert_called_once_with(config.agents[0])

        mock_graph.set_entry_point.assert_called_once_with("agent1_planner")

        nodes = {}
        for agent_config, mock_agent in zip(config.agents, mock_agents):
            nodes = {
                **nodes,
                agent_config.name: mock_agent.run,
                f"{agent_config.name}_planner": mock_planner_agent_class.return_value.run,
                f"{agent_config.name}_call_tool": mock_tool_executor_class.return_value.run,
                f"{agent_config.name}_plan_supervisor": mock_plan_supervisor_agent_class.return_value.run,
            }
        nodes["agent1_handover"] = mock_handover_agent_class.return_value.run

        mock_graph.add_node.assert_has_calls(
            [call(node_name, node_func) for node_name, node_func in nodes.items()]
        )

        edges = [
            ("agent1_planner", "agent1"),
            ("agent1_call_tool", "agent1_plan_supervisor"),
            ("agent1_plan_supervisor", "agent1"),
            ("agent2_planner", "agent2"),
            ("agent2_call_tool", "agent2_plan_supervisor"),
            ("agent2_plan_supervisor", "agent2"),
            ("agent1_handover", "agent2_planner"),
        ]
        mock_graph.add_edge.assert_has_calls(
            [call(start_node, end_node) for start_node, end_node in edges]
        )

        conditional_edges = [
            (
                "agent1",
                _graph_with_planning_router,
                {
                    "call_tool": "agent1_call_tool",
                    "supervisor": "agent1_plan_supervisor",
                    "next": "agent1_handover",
                },
            ),
            (
                "agent2",
                _graph_with_planning_router,
                {
                    "call_tool": "agent2_call_tool",
                    "supervisor": "agent2_plan_supervisor",
                    "next": END,
                },
            ),
        ]
        mock_graph.add_conditional_edges.assert_has_calls(
            [
                call(start_node, router_fnc, routes)
                for start_node, router_fnc, routes in conditional_edges
            ]
        )
        mock_graph.compile.assert_called_once()
