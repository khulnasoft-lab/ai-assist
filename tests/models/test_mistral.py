from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from mistralai.client import MistralClient

from ai_gateway.models import MistralChatModel, MistralTextGenModel
from ai_gateway.models.base_chat import Message, Role
from ai_gateway.models.base_text import TextGenModelOutput


class TestMistralChatMode:
    @pytest.fixture
    def mistral_client(self, monkeypatch):
        monkeypatch.setenv("MISTRAL_API_KEY", "test")
        return MistralClient()

    @pytest.fixture
    def api_key(self):
        return "specified-api-key"

    @pytest.fixture
    def mistral_chat_model(self, api_key, mistral_client):
        return MistralChatModel.from_model_name(
            name="mistral",
            api_key=api_key,
            client=mistral_client,
        )

    @pytest.mark.parametrize("model_name", ["mistral", "mixtral"])
    def test_from_model_name(self, model_name: str, api_key, mistral_client):
        model = MistralChatModel.from_model_name(
            name=model_name, api_key=api_key, client=mistral_client
        )

        assert model.api_key == "specified-api-key"
        assert model.metadata.engine == "mistral"
        assert model.metadata.name == model_name

    @pytest.mark.asyncio
    async def test_generate(self, mistral_chat_model, api_key):
        expected_messages = [{"role": "user", "content": "Test message"}]

        with patch(
            "ai_gateway.models.mistral.MistralClient.completion"
        ) as mock_completion:
            mock_completion.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="Test response"))]
            )
            messages = [Message(content="Test message", role="user")]
            output = await mistral_chat_model.generate(messages)
            assert isinstance(output, TextGenModelOutput)
            assert output.text == "Test response"

            mock_completion.assert_called_with(
                model=mistral_chat_model.metadata.name,
                messages=expected_messages,
                stream=False,
                temperature=0.2,
                top_p=0.95,
                max_tokens=2048,
                stop=["</new_code>"],
            )

    @pytest.mark.asyncio
    async def test_generate_stream(self, mistral_chat_model):
        expected_messages = [{"role": "user", "content": "Test message"}]

        streamed_response = iter(
            [MagicMock(choices=[Mock(delta=Mock(content="Streamed content"))])]
        )

        with patch(
            "ai_gateway.models.mistral.MistralClient.completion_stream"
        ) as mock_completion_stream, patch(
            "ai_gateway.instrumentators.model_requests.ModelRequestInstrumentator.watch"
        ) as mock_watch:
            watcher = Mock()
            mock_watch.return_value.__enter__.return_value = watcher

            mock_completion_stream.return_value = streamed_response

            messages = [Message(content="Test message", role="user")]
            response = await mistral_chat_model.generate(
                messages=messages,
                stream=True,
                temperature=0.3,
                top_p=0.9,
                top_k=25,
                max_output_tokens=1024,
            )

            content = []
            async for chunk in response:
                content.append(chunk.text)
            assert content == ["Streamed content"]

            mock_completion_stream.assert_called_with(
                model=mistral_chat_model.metadata.name,
                messages=expected_messages,
                stream=True,
                temperature=0.3,
                top_p=0.9,
                max_tokens=1024,
                stop=["</new_code>"],
            )

            mock_watch.assert_called_once_with(stream=True)
            watcher.finish.assert_called_once()


class TestMistralTextGenModel:
    @pytest.fixture
    def mistral_client(self, monkeypatch):
        monkeypatch.setenv("MISTRAL_API_KEY", "test")
        return MistralClient()

    @pytest.fixture
    def api_key(self):
        return "specified-api-key"

    @pytest.fixture
    def mistral_text_model(self, api_key, mistral_client):
        return MistralTextGenModel.from_model_name(
            name="codestral-latest",
            api_key=api_key,
            client=mistral_client,
        )

    @pytest.mark.parametrize("model_name", ["codestral-latest"])
    def test_from_model_name(self, model_name: str, api_key, mistral_client):
        model = MistralTextGenModel.from_model_name(
            name=model_name,
            client=mistral_client,
            api_key=api_key,
        )

        assert model.metadata.name == "codestral-latest"
        assert model.api_key == "specified-api-key"
        assert model.metadata.engine == "mistral"

    @pytest.mark.asyncio
    async def test_generate(self, mistral_text_model):
        with patch(
            "ai_gateway.models.mistral.MistralClient.completion"
        ) as mock_completion:
            mock_completion.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="Test response"))]
            )
            _generate_args = {
                "stream": False,
                "temperature": 0.9,
                "max_output_tokens": 10,
                "top_p": 0.95,
                "top_k": 0,
            }
            output = await mistral_text_model.generate(
                prefix="def hello_world():", **_generate_args
            )
            assert isinstance(output, TextGenModelOutput)
            assert output.text == "Test response"

    @pytest.mark.asyncio
    async def test_generate_stream(self, mistral_text_model):
        streamed_response = iter(
            [MagicMock(choices=[Mock(delta=Mock(content="Streamed content"))])]
        )

        with patch(
            "ai_gateway.models.mistral.MistralClient.completion_stream"
        ) as mock_completion_stream, patch(
            "ai_gateway.instrumentators.model_requests.ModelRequestInstrumentator.watch"
        ) as mock_watch:
            watcher = Mock()
            mock_watch.return_value.__enter__.return_value = watcher

            mock_completion_stream.return_value = streamed_response

            response = await mistral_text_model.generate(
                prefix="Test message",
                stream=True,
            )

            content = []
            async for chunk in response:
                content.append(chunk.text)
            assert content == ["Streamed content"]

            mock_watch.assert_called_once_with(stream=True)
            watcher.finish.assert_called_once()
