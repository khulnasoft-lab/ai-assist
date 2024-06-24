from enum import Enum

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from autograph.agents import (
    Agent,
    HandoverAgent,
    HandoverTool,
    PlannerAgent,
    PlanSupervisorAgent,
)
from autograph.agents.tool_executor import ToolExecutor
from autograph.entities import WorkflowConfig, WorkflowState


class SequentialGraphWithPlanningRoutes(str, Enum):
    CALL_TOOL = "call_tool"
    NEXT = "next"
    SUPERVISOR = "supervisor"


def _call_tool_node(agent_name: str) -> str:
    return f"{agent_name}_call_tool"


def _plan_supervisor_node(agent_name: str) -> str:
    return f"{agent_name}_plan_supervisor"


def _handover_node(agent_name: str) -> str:
    return f"{agent_name}_handover"


def _planner_node(agent_name: str) -> str:
    return f"{agent_name}_planner"


def _conditional_routing(
    agent_name: str,
) -> dict[SequentialGraphWithPlanningRoutes, str]:
    return {
        SequentialGraphWithPlanningRoutes.CALL_TOOL: _call_tool_node(agent_name),
        SequentialGraphWithPlanningRoutes.SUPERVISOR: _plan_supervisor_node(agent_name),
        SequentialGraphWithPlanningRoutes.NEXT: _handover_node(agent_name),
    }


def _graph_with_planning_router(state) -> SequentialGraphWithPlanningRoutes:
    # This is the router
    messages = state["messages"]
    last_message = messages[-1]

    if not last_message.tool_calls:
        return SequentialGraphWithPlanningRoutes.SUPERVISOR

    if last_message.tool_calls[0]["name"] == HandoverTool.__name__:
        return SequentialGraphWithPlanningRoutes.NEXT

    return SequentialGraphWithPlanningRoutes.CALL_TOOL


def graph_with_planning(config: WorkflowConfig):
    graph = StateGraph(WorkflowState)
    agent_configs = {}

    for agent_config in config.agents:
        # This is a placeholder for configurable tools
        tools = []  # type: ignore
        agent = Agent(config=agent_config)

        # HandoverTool is a special case where graph uses artificial tool for agents to mark completion of their action.
        # It is separate from tool list, as the tools is expected to be configurable by user with WorkflowConfig
        # while HandoverTool is internal implementation detail of this graph
        agent.setup(tools + [HandoverTool])
        agent_configs[agent_config.name] = agent_config

        graph.add_node(agent_config.name, agent.run)
        graph.add_node(
            _planner_node(agent_config.name),
            PlannerAgent(config=agent_config, team=[agent_config], tools=tools).run,
        )

        # HandoverTool only enforce agent to respond in restricted format to indicate completion of its work.
        # The HandoverTool therefore does not have any invocation and it being used in _graph_with_planning_router instead
        graph.add_node(_call_tool_node(agent_config.name), ToolExecutor(tools).run)
        graph.add_node(
            _plan_supervisor_node(agent_config.name),
            PlanSupervisorAgent(agent_config).run,
        )

        graph.add_edge(_planner_node(agent_config.name), agent_config.name)
        graph.add_edge(
            _call_tool_node(agent_config.name), _plan_supervisor_node(agent_config.name)
        )
        graph.add_edge(_plan_supervisor_node(agent_config.name), agent_config.name)

    graph.set_entry_point(_planner_node(config.workflow[0]))

    for next_agent_idx, agent_name in enumerate(config.workflow[:-1], start=1):
        agent_config = agent_configs[agent_name]
        graph.add_node(_handover_node(agent_name), HandoverAgent(agent_config).run)

        graph.add_conditional_edges(
            agent_name,
            _graph_with_planning_router,
            _conditional_routing(agent_name),  # type: ignore
        )
        graph.add_edge(
            _handover_node(agent_name), _planner_node(config.workflow[next_agent_idx])
        )

    last_agent_node = config.workflow[-1]

    last_node_routing = _conditional_routing(last_agent_node)
    last_node_routing[SequentialGraphWithPlanningRoutes.NEXT] = END

    graph.add_conditional_edges(
        last_agent_node, _graph_with_planning_router, last_node_routing  # type: ignore
    )

    return graph.compile(checkpointer=MemorySaver())
