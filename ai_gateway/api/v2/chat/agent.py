from typing import Annotated, AsyncIterator

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.responses import StreamingResponse

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.middleware import X_GITLAB_VERSION_HEADER
from ai_gateway.api.v2.chat.typing import AgentRequest
from ai_gateway.async_dependency_resolver import (
    get_container_application,
    get_internal_event_client,
)
from ai_gateway.auth.user import GitLabUser, get_current_user
from ai_gateway.chat.agents import (
    AgentStep,
    AgentToolAction,
    ReActAgent,
    ReActAgentInputs,
    TypeAgentEvent,
)
from ai_gateway.gitlab_features import GitLabFeatureCategory, GitLabUnitPrimitive
from ai_gateway.internal_events import InternalEventsClient

__all__ = [
    "router",
]


log = structlog.stdlib.get_logger("chat")

router = APIRouter()


async def get_react_agent():
    yield get_container_application().chat.react_agent()


async def _stream_handler(stream_events: AsyncIterator[TypeAgentEvent]):
    async for event in stream_events:
        yield f"{event.dump_as_response()}\n"


@router.post("/agent")
@feature_category(GitLabFeatureCategory.DUO_CHAT)
async def chat(
    request: Request,
    agent_request: AgentRequest,
    current_user: Annotated[GitLabUser, Depends(get_current_user)],
    react_agent: ReActAgent = Depends(get_react_agent),
    internal_event_client: InternalEventsClient = Depends(get_internal_event_client),
):
    if current_user.can(GitLabUnitPrimitive.DUO_CHAT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized to access duo chat",
        )

    internal_event_client.track_event(
        f"request_{GitLabUnitPrimitive.DUO_CHAT}",
        category=__name__,
    )

    scratchpad = [
        AgentStep(
            action=AgentToolAction(
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
        unavailable_resources=agent_request.unavailable_resources,
        additional_context=agent_request.options.additional_context,
        user=current_user,
        gl_version=request.headers.get(X_GITLAB_VERSION_HEADER, ""),
    )

    stream_events = react_agent.astream(inputs=inputs)

    return StreamingResponse(
        _stream_handler(stream_events), media_type="text/event-stream"
    )
