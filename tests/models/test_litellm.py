from typing import AsyncIterator, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ai_gateway.models import KindLiteLlmModel, LiteLlmChatModel
from ai_gateway.models.base import KindModelProvider
from ai_gateway.models.base_chat import Message, Role
from ai_gateway.models.base_text import TextGenModelChunk, TextGenModelOutput
from ai_gateway.models.litellm import LiteLlmTextGenModel


@pytest.fixture
<<<<<<< HEAD
def mock_vertex_ai_location():
    with patch("ai_gateway.models.litellm.Config") as mock:
        mock.return_value = Mock(vertex_text_model=Mock(location="mock-location"))

        yield mock


@pytest.fixture
def mock_vertex_ai_location_in_europe():
    with patch("ai_gateway.models.litellm.Config") as mock:
        mock.return_value = Mock(
            vertex_text_model=Mock(location="europe-mock-location")
        )

        yield mock
=======
def mock_litellm_acompletion():
    with patch("ai_gateway.models.litellm.acompletion") as mock_acompletion:
        mock_acompletion.return_value = AsyncMock(
            choices=[
                AsyncMock(message=AsyncMock(content="Test response")),
            ]
        )

        yield mock_acompletion


@pytest.fixture
def mock_litellm_atext_completion():
    with patch("ai_gateway.models.litellm.atext_completion") as mock_acompletion:
        mock_acompletion.return_value = AsyncMock(
            choices=[
                AsyncMock(text="Test text completion response"),
            ]
        )

        yield mock_acompletion
>>>>>>> c54a996d (feat: add Codestral on Vertex for Code Completions)


class TestKindLiteLlmModel:
    def test_chat_model(self):
        assert KindLiteLlmModel.MISTRAL.chat_model() == "openai/mistral"
        assert KindLiteLlmModel.MIXTRAL.chat_model() == "openai/mixtral"
        assert KindLiteLlmModel.MIXTRAL_8X22B.chat_model() == "openai/mixtral_8x22b"
        assert KindLiteLlmModel.CODESTRAL.chat_model() == "openai/codestral"
        assert KindLiteLlmModel.CODEGEMMA_2B.chat_model() == "openai/codegemma_2b"
        assert KindLiteLlmModel.CODEGEMMA_7B.chat_model() == "openai/codegemma_7b"
        assert KindLiteLlmModel.CODEGEMMA.chat_model() == "openai/codegemma"
        assert (
            KindLiteLlmModel.CODELLAMA_13B_CODE.chat_model()
            == "openai/codellama_13b_code"
        )
        assert KindLiteLlmModel.CODELLAMA.chat_model() == "openai/codellama"
        assert KindLiteLlmModel.DEEPSEEKCODER.chat_model() == "openai/deepseekcoder"
        assert (
            KindLiteLlmModel.CODESTRAL.chat_model(provider=KindModelProvider.MISTRALAI)
            == "codestral/codestral"
        )

    def test_text_model(self):
        assert (
            KindLiteLlmModel.CODEGEMMA_2B.text_model()
            == "text-completion-openai/codegemma_2b"
        )
        assert (
            KindLiteLlmModel.CODESTRAL.text_model()
            == "text-completion-openai/codestral"
        )
        assert (
            KindLiteLlmModel.CODESTRAL.text_model(provider=KindModelProvider.MISTRALAI)
            == "text-completion-codestral/codestral"
        )
        assert (
            KindLiteLlmModel.CODESTRAL_2405.text_model(
                provider=KindModelProvider.VERTEX_AI
            )
            == "vertex_ai/codestral@2405"
        )


class TestLiteLlmChatMode:
    @pytest.fixture
    def endpoint(self):
        return "http://127.0.0.1:1111/v1"

    @pytest.fixture
    def api_key(self):
        return "specified-api-key"

    @pytest.fixture
    def lite_llm_chat_model(self, endpoint, api_key):
        return LiteLlmChatModel.from_model_name(
            name="mistral",
            endpoint=endpoint,
            api_key=api_key,
            custom_models_enabled=True,
        )

    @pytest.mark.parametrize(
        (
            "model_name",
            "api_key",
            "provider",
            "custom_models_enabled",
            "provider_keys",
            "expected_name",
            "expected_api_key",
            "expected_engine",
        ),
        [
            (
                "mistral",
                "",
                KindModelProvider.LITELLM,
                True,
                {},
                "openai/mistral",
                "stubbed-api-key",
                "litellm",
            ),
            (
                "mixtral",
                None,
                KindModelProvider.LITELLM,
                True,
                {},
                "openai/mixtral",
                "stubbed-api-key",
                "litellm",
            ),
            (
                "codestral",
                "",
                KindModelProvider.MISTRALAI,
                True,
                {},
                "codestral/codestral",
                "stubbed-api-key",
                "codestral",
            ),
            (
                "codestral",
                None,
                KindModelProvider.MISTRALAI,
                True,
                {"mistral_api_key": "stubbed-api-key"},
                "codestral/codestral",
                "stubbed-api-key",
                "codestral",
            ),
        ],
    )
    def test_from_model_name(
        self,
        model_name: str,
        api_key: Optional[str],
        provider: KindModelProvider,
        custom_models_enabled: bool,
        provider_keys: dict,
        expected_name: str,
        expected_api_key: str,
        expected_engine: str,
        endpoint,
    ):
        model = LiteLlmChatModel.from_model_name(
            name=model_name,
            api_key=api_key,
            endpoint=endpoint,
            custom_models_enabled=custom_models_enabled,
            provider=provider,
            provider_keys=provider_keys,
        )

        assert model.metadata.name == expected_name
        assert model.endpoint == endpoint
        assert model.api_key == expected_api_key
        assert model.metadata.engine == expected_engine

        model = LiteLlmChatModel.from_model_name(name=model_name, api_key=None)

        assert model.endpoint is None
        assert model.api_key == "stubbed-api-key"

        if provider == KindModelProvider.LITELLM:
            with pytest.raises(ValueError) as exc:
                LiteLlmChatModel.from_model_name(name=model_name, endpoint=endpoint)
            assert str(exc.value) == "specifying custom models endpoint is disabled"

            with pytest.raises(ValueError) as exc:
                LiteLlmChatModel.from_model_name(name=model_name, api_key="api-key")
            assert str(exc.value) == "specifying custom models endpoint is disabled"

    @pytest.mark.asyncio
    async def test_generate(self, lite_llm_chat_model, endpoint, api_key):
        expected_messages = [{"role": "user", "content": "Test message"}]

        with patch("ai_gateway.models.litellm.acompletion") as mock_acompletion:
            mock_acompletion.return_value = AsyncMock(
                choices=[AsyncMock(message=AsyncMock(content="Test response"))]
            )
            messages = [Message(content="Test message", role="user")]
            output = await lite_llm_chat_model.generate(messages)
            assert isinstance(output, TextGenModelOutput)
            assert output.text == "Test response"

            mock_acompletion.assert_called_with(
                lite_llm_chat_model.metadata.name,
                messages=expected_messages,
                stream=False,
                temperature=0.2,
                top_p=0.95,
                top_k=40,
                max_tokens=2048,
                api_key=api_key,
                api_base=endpoint,
                timeout=30.0,
                stop=["</new_code>"],
            )

    @pytest.mark.asyncio
    async def test_generate_stream(self, lite_llm_chat_model, endpoint, api_key):
        expected_messages = [{"role": "user", "content": "Test message"}]

        streamed_response = AsyncMock()
        streamed_response.__aiter__.return_value = iter(
            [
                AsyncMock(
                    choices=[AsyncMock(delta=AsyncMock(content="Streamed content"))]
                )
            ]
        )

        with patch("ai_gateway.models.litellm.acompletion") as mock_acompletion, patch(
            "ai_gateway.instrumentators.model_requests.ModelRequestInstrumentator.watch"
        ) as mock_watch:
            watcher = Mock()
            mock_watch.return_value.__enter__.return_value = watcher

            mock_acompletion.return_value = streamed_response

            messages = [Message(content="Test message", role="user")]
            response = await lite_llm_chat_model.generate(
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

            mock_acompletion.assert_called_with(
                lite_llm_chat_model.metadata.name,
                messages=expected_messages,
                stream=True,
                temperature=0.3,
                top_p=0.9,
                top_k=25,
                max_tokens=1024,
                api_key=api_key,
                api_base=endpoint,
                timeout=30.0,
                stop=["</new_code>"],
            )

            mock_watch.assert_called_once_with(stream=True)
            watcher.finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_stream_instrumented(self, lite_llm_chat_model):
        async def mock_stream(*args, **kwargs):
            completions = [
                AsyncMock(
                    choices=[AsyncMock(delta=AsyncMock(content="Streamed content"))]
                ),
                "break here",
            ]
            for item in completions:
                if item == "break here":
                    raise ValueError("broken")
                yield item

        with patch("ai_gateway.models.litellm.acompletion") as mock_acompletion, patch(
            "ai_gateway.instrumentators.model_requests.ModelRequestInstrumentator.watch"
        ) as mock_watch:
            watcher = Mock()
            mock_watch.return_value.__enter__.return_value = watcher

            mock_acompletion.side_effect = AsyncMock(side_effect=mock_stream)

            messages = [Message(content="Test message", role="user")]
            response = await lite_llm_chat_model.generate(
                messages=messages, stream=True
            )

            watcher.finish.assert_not_called()

            with pytest.raises(ValueError):
                _ = [item async for item in response]

            mock_watch.assert_called_once_with(stream=True)
            watcher.register_error.assert_called_once()
            watcher.finish.assert_called_once()


class TestLiteLlmTextGenModel:
    @pytest.fixture
    def endpoint(self):
        return "http://127.0.0.1:4000"

    @pytest.fixture
    def api_key(self):
        return "specified-api-key"

    @pytest.fixture
    def provider_keys(self):
        return {"mistral_api_key": "codestral-api-key"}

    @pytest.fixture
    def lite_llm_text_model(self, endpoint, api_key):
        return LiteLlmTextGenModel.from_model_name(
            name="codegemma_2b",
            endpoint=endpoint,
            api_key=api_key,
            custom_models_enabled=True,
        )

    @pytest.mark.parametrize(
        (
            "model_name",
            "api_key",
            "provider",
            "custom_models_enabled",
            "provider_keys",
            "expected_name",
            "expected_api_key",
            "expected_engine",
        ),
        [
            (
                "codegemma_2b",
                "",
                KindModelProvider.LITELLM,
                True,
                {},
                "text-completion-openai/codegemma_2b",
                "stubbed-api-key",
                "litellm",
            ),
            (
                "codegemma_2b",
                None,
                KindModelProvider.LITELLM,
                True,
                {},
                "text-completion-openai/codegemma_2b",
                "stubbed-api-key",
                "litellm",
            ),
            (
                "codestral",
                None,
                KindModelProvider.MISTRALAI,
                True,
                {},
                "text-completion-codestral/codestral",
                "stubbed-api-key",
                "codestral",
            ),
            (
                "codestral",
                "",
                KindModelProvider.MISTRALAI,
                True,
                {"mistral_api_key": "stubbed-api-key"},
                "text-completion-codestral/codestral",
                "stubbed-api-key",
                "codestral",
            ),
        ],
    )
    def test_from_model_name(
        self,
        model_name: str,
        api_key: Optional[str],
        provider: KindModelProvider,
        custom_models_enabled: bool,
        provider_keys: dict,
        expected_name: str,
        expected_api_key: str,
        expected_engine: str,
        endpoint,
    ):
        model = LiteLlmTextGenModel.from_model_name(
            name=model_name,
            api_key=api_key,
            endpoint=endpoint,
            custom_models_enabled=custom_models_enabled,
            provider=provider,
            provider_keys=provider_keys,
        )

        assert model.metadata.name == expected_name
        assert model.endpoint == endpoint
        assert model.api_key == expected_api_key
        assert model.metadata.engine == expected_engine

        model = LiteLlmTextGenModel.from_model_name(name=model_name, api_key=None)

        assert model.endpoint is None
        assert model.api_key == "stubbed-api-key"

        if provider == KindModelProvider.LITELLM:
            with pytest.raises(ValueError) as exc:
                LiteLlmTextGenModel.from_model_name(name=model_name, endpoint=endpoint)
            assert str(exc.value) == "specifying custom models endpoint is disabled"

            with pytest.raises(ValueError) as exc:
                LiteLlmTextGenModel.from_model_name(name=model_name, api_key="api-key")
            assert str(exc.value) == "specifying custom models endpoint is disabled"

        if provider == KindModelProvider.VERTEX_AI:
            with pytest.raises(ValueError) as exc:
                LiteLlmTextGenModel.from_model_name(name=model_name, endpoint=endpoint)
            assert (
                str(exc.value)
                == "specifying api endpoint or key for vertex-ai provider is disabled"
            )

            with pytest.raises(ValueError) as exc:
                LiteLlmTextGenModel.from_model_name(name=model_name, api_key="api-key")
            assert (
                str(exc.value)
                == "specifying api endpoint or key for vertex-ai provider is disabled"
            )

    @pytest.mark.asyncio
    async def test_generate(
        self,
        mock_litellm_acompletion: Mock,
        mock_litellm_atext_completion: Mock,
        lite_llm_text_model,
        endpoint,
        api_key,
    ):
        _generate_args = {
            "stream": False,
            "temperature": 0.9,
            "max_output_tokens": 10,
            "top_p": 0.95,
            "top_k": 0,
        }
        output = await lite_llm_text_model.generate(
            prefix="def hello_world():", **_generate_args
        )

        assert mock_litellm_acompletion.called
        assert not mock_litellm_atext_completion.called

        assert isinstance(output, TextGenModelOutput)
        assert output.text == "Test response"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        (
            "model_name",
            "provider",
            "custom_models_enabled",
            "model_completion_args",
        ),
        [
            (
                "codegemma",
                KindModelProvider.LITELLM,
                True,
                {
                    "model": "text-completion-openai/codegemma",
                    "stop": [
                        "<|fim_prefix|>",
                        "<|fim_suffix|>",
                        "<|fim_middle|>",
                        "<|file_separator|>",
                    ],
                },
            ),
            (
                "codestral",
                KindModelProvider.MISTRALAI,
                True,
                {
                    "model": "text-completion-codestral/codestral",
                    "stop": [],
                    "api_key": "codestral-api-key",
                },
            ),
        ],
    )
    async def test_generate_with_acompletion(
        self,
        model_name,
        provider,
        custom_models_enabled,
        model_completion_args,
        endpoint,
        api_key,
        provider_keys,
        mock_litellm_acompletion: Mock,
        mock_litellm_atext_completion: Mock,
    ):
        litellm_model = LiteLlmTextGenModel.from_model_name(
            name=model_name,
            provider=provider,
            endpoint=endpoint,
            api_key=api_key,
            custom_models_enabled=custom_models_enabled,
            provider_keys=provider_keys,
        )

        output = await litellm_model.generate(
            prefix="def hello_world():",
        )

        expected_completion_args = {
            "max_tokens": 16,
            "temperature": 0.95,
            "top_p": 0.95,
            "stream": False,
            "timeout": 30.0,
            "api_key": api_key,
            "api_base": endpoint,
            "messages": [{"content": "def hello_world():", "role": Role.USER}],
        }
        expected_completion_args.update(model_completion_args)

        mock_litellm_acompletion.assert_called_with(**expected_completion_args)
        assert not mock_litellm_atext_completion.called

        assert isinstance(output, TextGenModelOutput)
        assert output.text == "Test response"

    @pytest.mark.asyncio
    async def test_generate_vertex_codestral(
        self,
        mock_vertex_ai_location: Mock,
        mock_litellm_acompletion: Mock,
        mock_litellm_atext_completion: Mock,
    ):
        lite_llm_vertex_codestral_model = LiteLlmTextGenModel.from_model_name(
            name=KindLiteLlmModel.CODESTRAL_2405,
            provider=KindModelProvider.VERTEX_AI,
        )

        output = await lite_llm_vertex_codestral_model.generate(
            prefix="func hello(name){",
            suffix="}",
            temperature=0.7,
            max_output_tokens=128,
        )

        assert not mock_litellm_acompletion.called

        mock_litellm_atext_completion.assert_called_with(
            model="vertex_ai/codestral@2405",
            prompt="func hello(name){",
            suffix="}",
            vertex_ai_location="us-central1",
            max_tokens=128,
            temperature=0.7,
            top_p=0.95,
            stream=False,
            timeout=60.0,
            stop=[
                "[INST]",
                "[/INST]",
                "[PREFIX]",
                "[MIDDLE]",
                "[SUFFIX]",
            ],
        )

        assert isinstance(output, TextGenModelOutput)
        assert output.text == "Test text completion response"

    @pytest.mark.asyncio
    async def test_generate_vertex_codestral_in_europe(
        self,
        mock_vertex_ai_location_in_europe: Mock,
        mock_litellm_atext_completion: Mock,
    ):
        lite_llm_vertex_codestral_model = LiteLlmTextGenModel.from_model_name(
            name=KindLiteLlmModel.CODESTRAL_2405,
            provider=KindModelProvider.VERTEX_AI,
        )

        await lite_llm_vertex_codestral_model.generate(
            prefix="func hello(name){",
            suffix="}",
        )

        _args, kwargs = mock_litellm_atext_completion.call_args
        assert kwargs["vertex_ai_location"] == "europe-west4"

    @pytest.mark.asyncio
    async def test_generate_stream(self, lite_llm_text_model, endpoint, api_key):
        streamed_response = AsyncMock()
        streamed_response.__aiter__.return_value = iter(
            [
                AsyncMock(
                    choices=[AsyncMock(delta=AsyncMock(content="Streamed content"))]
                )
            ]
        )

        with patch("ai_gateway.models.litellm.acompletion") as mock_acompletion, patch(
            "ai_gateway.instrumentators.model_requests.ModelRequestInstrumentator.watch"
        ) as mock_watch:
            watcher = Mock()
            mock_watch.return_value.__enter__.return_value = watcher

            mock_acompletion.return_value = streamed_response

            response = await lite_llm_text_model.generate(
                prefix="Test message",
                stream=True,
            )

            content = []
            async for chunk in response:
                content.append(chunk.text)
            assert content == ["Streamed content"]

            mock_watch.assert_called_once_with(stream=True)
            watcher.finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_stream_instrumented(self, lite_llm_text_model):
        async def mock_stream(*args, **kwargs):
            completions = [
                AsyncMock(
                    choices=[AsyncMock(delta=AsyncMock(content="Streamed content"))]
                ),
                "break here",
            ]
            for item in completions:
                if item == "break here":
                    raise ValueError("broken")
                yield item

        with patch("ai_gateway.models.litellm.acompletion") as mock_acompletion, patch(
            "ai_gateway.instrumentators.model_requests.ModelRequestInstrumentator.watch"
        ) as mock_watch:
            watcher = Mock()
            mock_watch.return_value.__enter__.return_value = watcher

            mock_acompletion.side_effect = AsyncMock(side_effect=mock_stream)

            response = await lite_llm_text_model.generate(
                prefix="Test message", stream=True
            )

            watcher.finish.assert_not_called()

            with pytest.raises(ValueError):
                _ = [item async for item in response]

            mock_watch.assert_called_once_with(stream=True)
            watcher.register_error.assert_called_once()
            watcher.finish.assert_called_once()
