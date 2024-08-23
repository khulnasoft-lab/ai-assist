from typing import Annotated, AsyncIterator

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.responses import StreamingResponse

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.middleware import X_GITLAB_VERSION_HEADER
from ai_gateway.api.v2.chat.typing import AgentRequest, AgentStreamResponseEvent
from ai_gateway.async_dependency_resolver import (
    get_container_application,
    get_internal_event_client,
)
from ai_gateway.auth.user import GitLabUser, get_current_user
from ai_gateway.chat.agents import (
    AgentStep,
    AgentToolAction,
    ReActAgentInputs,
    ReActAgentToolAction,
    TypeReActAgentAction,
)
from ai_gateway.chat.executor import GLAgentRemoteExecutor
from ai_gateway.gitlab_features import (
    GitLabFeatureCategory,
    GitLabUnitPrimitive,
    WrongUnitPrimitives,
)
from ai_gateway.internal_events import InternalEventsClient

__all__ = [
    "router",
]


log = structlog.stdlib.get_logger("chat")

router = APIRouter()


async def get_gl_agent_remote_executor():
    yield get_container_application().chat.gl_agent_remote_executor()

# tgao
# CHAT_V2_ENDPOINT
@router.post("/agent")
@feature_category(GitLabFeatureCategory.DUO_CHAT)
async def chat(
    request: Request,
    agent_request: AgentRequest,
    current_user: Annotated[GitLabUser, Depends(get_current_user)],
    gl_agent_remote_executor: GLAgentRemoteExecutor[
        ReActAgentInputs, TypeReActAgentAction
    ] = Depends(get_gl_agent_remote_executor),
    internal_event_client: InternalEventsClient = Depends(get_internal_event_client),
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
        current_file=agent_request.options.current_file,
        model_metadata=agent_request.model_metadata,
        additional_context=agent_request.options.additional_context,
    )

    try:
        gl_version = request.headers.get(X_GITLAB_VERSION_HEADER, "")
        gl_agent_remote_executor.on_behalf(current_user, gl_version)
    except WrongUnitPrimitives as ex:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to access duo chat",
        ) from ex

    # TODO: Refactor `gl_agent_remote_executor.on_behalf` to return accessed unit primitives for tool filtering.
    internal_event_client.track_event(
        f"request_{GitLabUnitPrimitive.DUO_CHAT}",
        category=__name__,
    )

    stream_actions = gl_agent_remote_executor.stream(inputs=inputs)

    return StreamingResponse(
        _stream_handler(stream_actions), media_type="text/event-stream"
    )
