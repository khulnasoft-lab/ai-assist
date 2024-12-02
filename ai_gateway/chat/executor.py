from typing import AsyncIterator, Generic

import starlette_context

from ai_gateway.chat.agents import (
    AgentError,
    AgentToolAction,
    ReActAgent,
    TypeAgentEvent,
    TypeAgentInputs,
)
from ai_gateway.chat.tools import BaseTool
from ai_gateway.internal_events import InternalEventsClient

__all__ = [
    "GLAgentRemoteExecutor",
]

from ai_gateway.structured_logging import get_request_logger

_REACT_AGENT_AVAILABLE_TOOL_NAMES_CONTEXT_KEY = "duo_chat.agent_available_tools"

log = get_request_logger("gl_agent_remote_executor")


class GLAgentRemoteExecutor(Generic[TypeAgentInputs, TypeAgentEvent]):
    def __init__(
        self,
        *,
        agent: ReActAgent,
        tools: list[BaseTool],
        internal_event_client: InternalEventsClient,
    ):
        self.agent = agent
        self.tools = tools
        self.internal_event_client = internal_event_client

    @property
    def tools_by_name(self) -> dict:
        return {tool.name: tool for tool in self.tools}

    async def stream(self, *, inputs: TypeAgentInputs) -> AsyncIterator[TypeAgentEvent]:
        inputs.tools = self.tools
        tools_by_name = self.tools_by_name

        starlette_context.context[_REACT_AGENT_AVAILABLE_TOOL_NAMES_CONTEXT_KEY] = list(
            tools_by_name.keys()
        )

        log.info("Processed inputs", source=__name__, inputs=inputs)

        async for event in self.agent.astream(inputs):
            if isinstance(event, AgentToolAction):
                if event.tool in tools_by_name:
                    tool = tools_by_name[event.tool]
                    self.internal_event_client.track_event(
                        f"request_{tool.unit_primitive}",
                        category=__name__,
                    )
                    yield event
                else:
                    yield AgentError(message="tool not available", retryable=False)
            else:
                yield event
