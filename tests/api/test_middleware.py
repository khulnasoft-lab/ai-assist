from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request

from ai_gateway.api.middleware import (
    X_GITLAB_GLOBAL_USER_ID_HEADER,
    X_GITLAB_HOST_NAME_HEADER,
    X_GITLAB_INSTANCE_ID_HEADER,
    X_GITLAB_REALM_HEADER,
    X_GITLAB_VERSION_HEADER,
    InternalEventMiddleware,
)
from ai_gateway.internal_events import EventContext


@pytest.fixture
def mock_app():
    return AsyncMock()


@pytest.fixture
def middleware(mock_app):
    return InternalEventMiddleware(
        mock_app, skip_endpoints=["/health"], enabled=True, environment="test"
    )


@pytest.mark.asyncio
async def test_middleware_non_http_request(middleware):
    scope = {"type": "websocket"}
    receive = AsyncMock()
    send = AsyncMock()

    with patch("ai_gateway.api.middleware.current_event_context") as mock_event_context:
        await middleware(scope, receive, send)
        mock_event_context.set.assert_not_called()

    middleware.app.assert_called_once_with(scope, receive, send)


@pytest.mark.asyncio
async def test_middleware_disabled(mock_app):
    middleware = InternalEventMiddleware(
        mock_app, skip_endpoints=[], enabled=False, environment="test"
    )
    request = Request({"type": "http"})
    scope = request.scope
    receive = AsyncMock()
    send = AsyncMock()

    with patch("ai_gateway.api.middleware.current_event_context") as mock_event_context:
        await middleware(scope, receive, send)
        mock_event_context.set.assert_not_called()

    middleware.app.assert_called_once_with(scope, receive, send)


@pytest.mark.asyncio
async def test_middleware_skip_path(middleware):
    request = Request(
        {
            "type": "http",
            "path": "/health",
            "headers": [],
        }
    )
    scope = request.scope
    receive = AsyncMock()
    send = AsyncMock()

    with patch("ai_gateway.api.middleware.current_event_context") as mock_event_context:
        await middleware(scope, receive, send)
        mock_event_context.set.assert_not_called()

    middleware.app.assert_called_once_with(scope, receive, send)


@pytest.mark.asyncio
async def test_middleware_set_context(middleware):
    request = Request(
        {
            "type": "http",
            "path": "/api/endpoint",
            "headers": [
                (b"user-agent", b"TestAgent"),
                (X_GITLAB_REALM_HEADER.lower().encode(), b"test-realm"),
                (X_GITLAB_INSTANCE_ID_HEADER.lower().encode(), b"test-instance"),
                (X_GITLAB_HOST_NAME_HEADER.lower().encode(), b"test-host"),
                (X_GITLAB_VERSION_HEADER.lower().encode(), b"test-version"),
                (X_GITLAB_GLOBAL_USER_ID_HEADER.lower().encode(), b"test-user"),
            ],
        }
    )
    scope = request.scope
    receive = AsyncMock()
    send = AsyncMock()

    with patch("ai_gateway.api.middleware.current_event_context") as mock_event_context:
        await middleware(scope, receive, send)

        expected_context = EventContext(
            environment="test",
            source="TestAgent",
            realm="test-realm",
            instance_id="test-instance",
            host_name="test-host",
            instance_version="test-version",
            global_user_id="test-user",
        )
        mock_event_context.set.assert_called_once_with(expected_context)

    middleware.app.assert_called_once_with(scope, receive, send)


@pytest.mark.asyncio
async def test_middleware_missing_headers(middleware):
    request = Request(
        {
            "type": "http",
            "path": "/api/endpoint",
            "headers": [
                (b"user-agent", b"TestAgent"),
            ],
        }
    )
    scope = request.scope
    receive = AsyncMock()
    send = AsyncMock()

    with patch("ai_gateway.api.middleware.current_event_context") as mock_event_context:
        await middleware(scope, receive, send)

        expected_context = EventContext(
            environment="test",
            source="TestAgent",
            realm=None,
            instance_id=None,
            host_name=None,
            instance_version=None,
            global_user_id=None,
        )
        mock_event_context.set.assert_called_once_with(expected_context)

    middleware.app.assert_called_once_with(scope, receive, send)
