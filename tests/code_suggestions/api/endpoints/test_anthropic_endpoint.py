from unittest import mock
from unittest.mock import AsyncMock

import pytest
from anthropic import AsyncAnthropic
from anthropic.types import Completion
from fastapi.testclient import TestClient

from ai_gateway.api.v2.api import api_router
from ai_gateway.auth import User, UserClaims
from ai_gateway.models import AnthropicModel, SafetyAttributes, TextGenModelOutput


@pytest.fixture(scope="class")
def fast_api_router():
    return api_router


@pytest.fixture
def auth_user():
    return User(
        authenticated=True,
        claims=UserClaims(is_third_party_ai_default=False, scopes=["duo_chat"]),
    )


class TestAnthropicSuccessfulRequest:
    @pytest.mark.asyncio
    async def test_successful_response(
        self,
        mock_client: TestClient,
    ):
        mock_model = mock.Mock(spec=AnthropicModel)
        mock_model.generate = AsyncMock(
            return_value=TextGenModelOutput(
                text="love is everywhere",
                score=10000,
                safety_attributes=SafetyAttributes(),
            )
        )

        with mock.patch(
            "ai_gateway.api.v2.endpoints.anthropic.AnthropicModel"
        ) as mock_anthropic_model:
            mock_anthropic_model.from_model_name.return_value = mock_model
            response = mock_client.post(
                "/v2/anthropic",
                headers={
                    "Authorization": "Bearer 12345",
                    "X-Gitlab-Authentication-Type": "oidc",
                },
                json={
                    "prompt": "string",
                    "model": "claude-2",
                    "max_tokens_to_sample": 2048,
                    "stop_sequences": [],
                    "stream": False,
                    "temperature": 0.1,
                },
            )

        assert response.status_code == 200

        assert response.json()["completion"] == "love is everywhere"
        mock_model.generate.assert_called_with(
            prefix="string",
            _suffix="",
            max_tokens_to_sample=2048,
            stream=False,
            temperature=0.1,
            stop_sequences=[],
        )


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
                text="love is everywhere",
                score=10000,
                safety_attributes=SafetyAttributes(),
            )
        )

        with mock.patch(
            "ai_gateway.api.v2.endpoints.anthropic.AnthropicModel"
        ) as mock_anthropic_model:
            mock_anthropic_model.from_model_name.return_value = mock_model
            response = mock_client.post(
                "/v2/anthropic",
                headers={
                    "Authorization": "Bearer 12345",
                    "X-Gitlab-Authentication-Type": "oidc",
                },
                json={
                    "prompt": "string",
                    "model": "claude-2",
                    "max_tokens_to_sample": 2048,
                    "stop_sequences": [],
                    "stream": False,
                    "temperature": 0.1,
                },
            )

        assert response.status_code == 403
        assert response.json() == {"detail": "Forbidden"}


class TestAnthropicInvalidRequest:
    @pytest.mark.asyncio
    async def test_invalid_request(
        self,
        mock_client: TestClient,
    ):
        mock_model = mock.Mock(spec=AnthropicModel)
        mock_model.generate = AsyncMock(
            return_value=TextGenModelOutput(
                text="love is everywhere",
                score=10000,
                safety_attributes=SafetyAttributes(),
            )
        )

        with mock.patch(
            "ai_gateway.api.v2.endpoints.anthropic.AnthropicModel"
        ) as mock_anthropic_model:
            mock_anthropic_model.from_model_name.return_value = mock_model
            response = mock_client.post(
                "/v2/anthropic",
                headers={
                    "Authorization": "Bearer 12345",
                    "X-Gitlab-Authentication-Type": "oidc",
                },
                json={
                    "model": "claude-2",
                    "max_tokens_to_sample": 2048,
                    "stop_sequences": [],
                    "stream": False,
                    "temperature": 0.1,
                },
            )

        assert response.status_code == 422
        assert response.json() == {
            "detail": [
                {
                    "loc": ["body", "prompt"],
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ]
        }
