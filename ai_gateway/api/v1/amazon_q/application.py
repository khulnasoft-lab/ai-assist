from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from gitlab_cloud_connector import GitLabFeatureCategory, GitLabUnitPrimitive
from gitlab_cloud_connector.auth import AUTH_HEADER

from ai_gateway.api.auth_utils import StarletteUser, get_current_user
from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v1.amazon_q.typing import ApplicationRequest
from ai_gateway.async_dependency_resolver import (
    get_amazon_q_client_factory,
    get_internal_event_client,
)
from ai_gateway.integrations.amazon_q.client import AmazonQClientFactory
from ai_gateway.integrations.amazon_q.errors import AWSException
from ai_gateway.internal_events import InternalEventsClient

__all__ = [
    "router",
]

router = APIRouter()


@router.post("/application")
@feature_category(GitLabFeatureCategory.DUO_CHAT)
async def oauth_create_application(
    request: Request,
    application_request: ApplicationRequest,
    current_user: Annotated[StarletteUser, Depends(get_current_user)],
    internal_event_client: InternalEventsClient = Depends(get_internal_event_client),
    amazon_q_client_factory: AmazonQClientFactory = Depends(
        get_amazon_q_client_factory
    ),
):
    if not current_user.can(GitLabUnitPrimitive.AGENT_QUICK_ACTIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to perform action",
        )

    internal_event_client.track_event(
        f"request_{GitLabUnitPrimitive.AGENT_QUICK_ACTIONS}",
        category=__name__,
    )

    try:
        q_client = amazon_q_client_factory.get_client(
            current_user=current_user,
            auth_header=request.headers.get(AUTH_HEADER),
            role_arn=application_request.role_arn,
        )

        q_client.create_or_update_auth_application(application_request)
    except AWSException as e:
        raise e.to_http_exception()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
