from typing import Annotated, AsyncIterator

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from gitlab_cloud_connector import FeatureCategory, WrongUnitPrimitives
from starlette.responses import StreamingResponse

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v2.chat.typing import AgentRequest, AgentStreamResponseEvent
from ai_gateway.async_dependency_resolver import get_container_application
from ai_gateway.auth.user import GitLabUser, get_current_user
from ai_gateway.chat.agents import (
    AgentStep,
    AgentToolAction,
    ReActAgentInputs,
    ReActAgentToolAction,
    TypeReActAgentAction,
)
from ai_gateway.chat.executor import GLAgentRemoteExecutor

__all__ = [
    "router",
]


log = structlog.stdlib.get_logger("chat")

router = APIRouter()


async def get_gl_agent_remote_executor():
    yield get_container_application().chat.gl_agent_remote_executor()


@router.post("/agent")
@feature_category(FeatureCategory.DUO_CHAT)
async def chat(
    request: Request,
    agent_request: AgentRequest,
    current_user: Annotated[GitLabUser, Depends(get_current_user)],
    gl_agent_remote_executor: GLAgentRemoteExecutor[
        ReActAgentInputs, TypeReActAgentAction
    ] = Depends(get_gl_agent_remote_executor),
):
    async def _stream_handler(stream_actions: AsyncIterator[TypeReActAgentAction]):
        async for action in stream_actions:
            event_type = (
                "action"
                if isinstance(action, AgentToolAction)
                else "final_answer_delta"
            )

            event = AgentStreamResponseEvent(type=event_type, data=action)

            yield f"{event.model_dump_json()}\n"

    scratchpad = [
        AgentStep[TypeReActAgentAction](
            action=ReActAgentToolAction(
                thought=step.thought,
                tool=step.tool,
                tool_input=step.tool_input,
            ),
            observation=step.observation,
        )
        for step in agent_request.options.agent_scratchpad.steps
    ]

    inputs = ReActAgentInputs(
        question=agent_request.prompt,
        chat_history=agent_request.options.chat_history,
        agent_scratchpad=scratchpad,
        context=agent_request.options.context,
        current_file_context=agent_request.options.current_file_context,
        model_metadata=agent_request.model_metadata,
    )

    try:
        gl_agent_remote_executor.on_behalf(current_user)
    except WrongUnitPrimitives as ex:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to access duo chat",
        ) from ex

    stream_actions = gl_agent_remote_executor.stream(inputs=inputs)

    return StreamingResponse(
        _stream_handler(stream_actions), media_type="text/event-stream"
    )
