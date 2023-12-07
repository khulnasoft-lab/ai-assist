import os
from typing import AsyncIterator, Type
from unittest import mock
from unittest.mock import ANY, AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain.schema.output import ChatGenerationChunk
from structlog.testing import capture_logs

from ai_gateway.api.v1.api import api_router
from ai_gateway.auth import User, UserClaims
from ai_gateway.deps import ChatContainer
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
        claims=UserClaims(scopes=["duo_chat"]),
    )


class TestAgentSuccessfulRequest:
    @pytest.mark.asyncio
    async def test_successful_response(self, mock_client: TestClient):
        model_name = "claude-2.0"

        with patch(
            "ai_gateway.api.v1.chat.agent.ChatAnthropic.ainvoke"
        ) as mock_model_invoke:
            mock_model_invoke.return_value = "test completion"

            response = mock_client.post(
                "/v1/chat/agent",
                headers={
                    "Authorization": "Bearer 12345",
                    "X-Gitlab-Authentication-Type": "oidc",
                },
                json={
                    "prompt_components": [
                        {
                            "type": "prompt",
                            "metadata": {
                                "source": "gitlab-rails-sm",
                                "version": "16.5.0-ee",
                            },
                            "payload": {
                                "content": "\n\nHuman: hello, what is your name?\n\nAssistant:",
                                "provider": "anthropic",
                                "model": model_name,
                            },
                        },
                    ]
                },
            )

            mock_model_invoke.assert_called_with(
                "\n\nHuman: hello, what is your name?\n\nAssistant:", ANY
            )

        assert response.status_code == 200

        assert response.json()["response"] == "test completion"

        response_metadata = response.json()["metadata"]
        assert response_metadata["provider"] == "anthropic"
        assert response_metadata["model"] == model_name


class TestAgentSuccessfulStream:
    @pytest.mark.asyncio
    async def test_successful_stream(self, mock_client: TestClient):
        model_name = "claude-2.0"

        model_chunks = ["test", " ", "completion"]

        async def _stream_generator(*args) -> AsyncIterator[ChatGenerationChunk]:
            for chunk in model_chunks:
                yield chunk

        with patch(
            "ai_gateway.api.v1.chat.agent.ChatAnthropic.astream"
        ) as mock_model_stream:
            mock_model_stream.side_effect = _stream_generator

            response = mock_client.post(
                "/v1/chat/agent",
                headers={
                    "Authorization": "Bearer 12345",
                    "X-Gitlab-Authentication-Type": "oidc",
                },
                json={
                    "prompt_components": [
                        {
                            "type": "prompt",
                            "metadata": {
                                "source": "gitlab-rails-sm",
                                "version": "16.5.0-ee",
                            },
                            "payload": {
                                "content": "\n\nHuman: hello, how can I stream in FastAPI?\n\nAssistant:",
                                "provider": "anthropic",
                                "model": model_name,
                            },
                        },
                    ],
                    "stream": "True",
                },
            )

            mock_model_stream.assert_called_with(
                "\n\nHuman: hello, how can I stream in FastAPI?\n\nAssistant:", ANY
            )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert response.text == "test completion"


class TestAgentUnsupportedProvider:
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
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {
                            "source": "gitlab-rails-sm",
                            "version": "16.5.0-ee",
                        },
                        "payload": {
                            "content": "\n\nHuman: hello, what is your name?\n\nAssistant:",
                            "provider": "UNSUPPORTED_PROVIDER",
                            "model": "claude-2.0",
                        },
                    },
                ]
            },
        )

        assert response.status_code == 422
        assert response.json() == {
            "detail": [
                {
                    "loc": ["body", "prompt_components", 0, "payload", "provider"],
                    "msg": "unexpected value; permitted: 'anthropic'",
                    "type": "value_error.const",
                    "ctx": {
                        "given": "UNSUPPORTED_PROVIDER",
                        "permitted": ["anthropic"],
                    },
                }
            ]
        }


class TestAgentUnsupportedModel:
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
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {
                            "source": "gitlab-rails-sm",
                            "version": "16.5.0-ee",
                        },
                        "payload": {
                            "content": "\n\nHuman: hello, what is your name?\n\nAssistant:",
                            "provider": "anthropic",
                            "model": "UNSUPPORTED_MODEL",
                        },
                    },
                ]
            },
        )

        assert response.status_code == 422
        assert response.json() == {
            "detail": [
                {
                    "loc": ["body", "prompt_components", 0, "payload", "model"],
                    "msg": "unexpected value; permitted: 'claude-2.0', 'claude-instant-1.2'",
                    "type": "value_error.const",
                    "ctx": {
                        "given": "UNSUPPORTED_MODEL",
                        "permitted": ["claude-2.0", "claude-instant-1.2"],
                    },
                }
            ]
        }


class TestAnthropicInvalidScope:
    @pytest.fixture
    def auth_user(self):
        return User(
            authenticated=True,
            claims=UserClaims(scopes=["unauthorized_scope"]),
        )

    def test_invalid_scope(
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
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {
                            "source": "gitlab-rails-sm",
                            "version": "16.5.0-ee",
                        },
                        "payload": {
                            "content": "\n\nHuman: hello, what is your name?\n\nAssistant:",
                            "provider": "anthropic",
                            "model": "claude-2.0",
                        },
                    }
                ]
            },
        )

        assert response.status_code == 403
        assert response.json() == {"detail": "Forbidden"}


class TestAgentInvalidRequestMissingFields:
    def test_invalid_request_missing_fields(
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
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {"source": "gitlab-rails-sm"},
                        "payload": {
                            "provider": "anthropic",
                            "model": "claude-2.0",
                        },
                    },
                ]
            },
        )

        assert response.status_code == 422
        assert response.json() == {
            "detail": [
                {
                    "loc": ["body", "prompt_components", 0, "metadata", "version"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
                {
                    "loc": ["body", "prompt_components", 0, "payload", "content"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ]
        }


class TestAgentInvalidRequestManyPromptComponents:
    def test_invalid_request_many_prompt_components(
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
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {
                            "source": "gitlab-rails-sm",
                            "version": "16.5.0-ee",
                        },
                        "payload": {
                            "content": "\n\nHuman: hello, what is your name?\n\nAssistant:",
                            "provider": "anthropic",
                            "model": "claude-2.0",
                        },
                    },
                    {
                        "type": "prompt",
                        "metadata": {
                            "source": "vscode",
                            "version": "1.2.3",
                        },
                        "payload": {
                            "content": "SECOND PROMPT COMPONENT (NOT EXPECTED)",
                            "provider": "anthropic",
                            "model": "claude-2.0",
                        },
                    },
                ]
            },
        )

        assert response.status_code == 422
        assert response.json() == {
            "detail": [
                {
                    "ctx": {"limit_value": 1},
                    "loc": ["body", "prompt_components"],
                    "msg": "ensure this value has at most 1 items",
                    "type": "value_error.list.max_items",
                }
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

        with patch(
            "ai_gateway.api.v1.chat.agent.ChatAnthropic.ainvoke"
        ) as mock_model_invoke:
            mock_model_invoke.side_effect = _side_effect

            with capture_logs() as cap_logs:
                response = mock_client.post(
                    "/v1/chat/agent",
                    headers={
                        "Authorization": "Bearer 12345",
                        "X-Gitlab-Authentication-Type": "oidc",
                    },
                    json={
                        "prompt_components": [
                            {
                                "type": "prompt",
                                "metadata": {
                                    "source": "gitlab-rails-sm",
                                    "version": "16.5.0-ee",
                                },
                                "payload": {
                                    "content": "\n\nHuman: hello, what is your name?\n\nAssistant:",
                                    "provider": "anthropic",
                                    "model": "claude-2.0",
                                },
                            }
                        ]
                    },
                )

        assert response.status_code == 200
        assert response.json()["response"] == ""

        assert cap_logs[0]["event"].startswith("failed to execute Anthropic request")
        assert cap_logs[0]["log_level"] == "error"
