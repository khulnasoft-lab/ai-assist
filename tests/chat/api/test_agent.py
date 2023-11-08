from typing import Type
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from structlog.testing import capture_logs

from ai_gateway.api.v1.api import api_router
from ai_gateway.auth import User, UserClaims
from ai_gateway.models import (
    AnthropicAPIConnectionError,
    AnthropicAPIStatusError,
    AnthropicModel,
    ModelAPIError,
    SafetyAttributes,
    TextGenModelOutput,
)


@pytest.fixture(scope="class")
def fast_api_router():
    return api_router


@pytest.fixture
def auth_user():
    return User(
        authenticated=True,
        claims=UserClaims(is_third_party_ai_default=False, scopes=["duo_chat"]),
    )


class TestAgentSuccessfulRequest:
    @pytest.mark.asyncio
    async def test_successful_response(
        self,
        mock_client: TestClient,
    ):
        mock_model = mock.Mock(spec=AnthropicModel)
        mock_model.generate = AsyncMock(
            return_value=TextGenModelOutput(
                text="test completion",
                score=10000,
                safety_attributes=SafetyAttributes(),
            )
        )

        with mock.patch(
            "ai_gateway.api.v1.chat.agent.AnthropicModel"
        ) as mock_anthropic_model:
            mock_anthropic_model.from_model_name.return_value = mock_model
            response = mock_client.post(
                "/v1/chat/agent",
                headers={
                    "Authorization": "Bearer 12345",
                    "X-Gitlab-Authentication-Type": "oidc",
                },
                json={
                    "type": "prompt",
                    "metadata": {"source": "gitlab-rails-sm", "version": "16.5.0-ee"},
                    "payload": {
                        "content": "\n\nHuman: hello, what is your name?\n\nAssistant:",
                        "provider": "anthropic",
                        "model": "claude-2",
                    },
                },
            )

        assert response.status_code == 200

        assert response.json()["response"] == "test completion"

        response_metadata = response.json()["metadata"]
        assert response_metadata["provider"] == "anthropic"
        assert response_metadata["model"] == "claude-2"

        mock_model.generate.assert_called_with(
            prefix="\n\nHuman: hello, what is your name?\n\nAssistant:",
            _suffix="",
            max_tokens_to_sample=2048,
            stream=False,
            temperature=0.1,
            stop_sequences=[],
        )


class TestAgentUnsupportedProvider:
    def test_invalid_request(
        self,
        mock_client: TestClient,
    ):
        with capture_logs() as cap_logs:
            response = mock_client.post(
                "/v1/chat/agent",
                headers={
                    "Authorization": "Bearer 12345",
                    "X-Gitlab-Authentication-Type": "oidc",
                },
                json={
                    "type": "prompt",
                    "metadata": {"source": "gitlab-rails-sm", "version": "16.5.0-ee"},
                    "payload": {
                        "content": "\n\nHuman: hello, what is your name?\n\nAssistant:",
                        "provider": "UNKNOWN PROVIDER",
                        "model": "claude-2",
                    },
                },
            )

            assert cap_logs[0]["event"] == "Unsupported provider: UNKNOWN PROVIDER"
            assert cap_logs[0]["log_level"] == "error"

            assert response.status_code == 422
            assert response.json().get("detail") == "Unsupported provider"


class TestAnthropicInvalidScope:
    @pytest.fixture
    def auth_user(self):
        return User(
            authenticated=True,
            claims=UserClaims(
                is_third_party_ai_default=False, scopes=["unauthorized_scope"]
            ),
        )

    @pytest.mark.asyncio
    async def test_invalid_scope(
        self,
        mock_client: TestClient,
    ):
        mock_model = mock.Mock(spec=AnthropicModel)
        mock_model.generate = AsyncMock(
            return_value=TextGenModelOutput(
                text="test completion",
                score=10000,
                safety_attributes=SafetyAttributes(),
            )
        )

        with mock.patch(
            "ai_gateway.api.v1.chat.agent.AnthropicModel"
        ) as mock_anthropic_model:
            mock_anthropic_model.from_model_name.return_value = mock_model
            response = mock_client.post(
                "/v1/chat/agent",
                headers={
                    "Authorization": "Bearer 12345",
                    "X-Gitlab-Authentication-Type": "oidc",
                },
                json={
                    "type": "prompt",
                    "metadata": {"source": "gitlab-rails-sm", "version": "16.5.0-ee"},
                    "payload": {
                        "content": "\n\nHuman: hello, what is your name?\n\nAssistant:",
                        "provider": "anthropic",
                        "model": "claude-2",
                    },
                },
            )

        assert response.status_code == 403
        assert response.json() == {"detail": "Forbidden"}


class TestAgentInvalidRequest:
    def test_invalid_request(
        self,
        mock_client: TestClient,
    ):
        response = mock_client.post(
            "/v1/chat/agent",
            headers={
                "Authorization": "Bearer 12345",
                "X-Gitlab-Authentication-Type": "oidc",
            },
            json={
                "type": "prompt",
                "metadata": {"source": "gitlab-rails-sm"},
                "payload": {
                    "provider": "anthropic",
                    "model": "claude-2",
                },
            },
        )

        assert response.status_code == 422
        assert response.json() == {
            "detail": [
                {
                    "loc": ["body", "metadata", "version"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
                {
                    "loc": ["body", "payload", "content"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ]
        }


class TestAgentUnsuccessfulAnthropicRequest:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "model_exception_type", [AnthropicAPIStatusError, AnthropicAPIConnectionError]
    )
    async def test_fail_receiving_anthropic_response(
        self, mock_client: TestClient, model_exception_type: Type[ModelAPIError]
    ):
        def _side_effect(*_args, **_kwargs):
            raise exception

        if issubclass(model_exception_type, AnthropicAPIStatusError):
            model_exception_type.code = 404
        exception = model_exception_type("exception message")

        mock_model = mock.Mock(spec=AnthropicModel)
        mock_model.generate = AsyncMock(
            side_effect=_side_effect,
        )

        with mock.patch(
            "ai_gateway.api.v1.chat.agent.AnthropicModel"
        ) as mock_anthropic_model:
            mock_anthropic_model.from_model_name.return_value = mock_model
            response = mock_client.post(
                "/v1/chat/agent",
                headers={
                    "Authorization": "Bearer 12345",
                    "X-Gitlab-Authentication-Type": "oidc",
                },
                json={
                    "type": "prompt",
                    "metadata": {"source": "gitlab-rails-sm", "version": "16.5.0-ee"},
                    "payload": {
                        "content": "\n\nHuman: hello, what is your name?\n\nAssistant:",
                        "provider": "anthropic",
                        "model": "claude-2",
                    },
                },
            )

        assert response.status_code == 500
        assert response.json() == {"detail": "Failed to obtain Anthropic response"}
