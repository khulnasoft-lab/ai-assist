from typing import Type
from unittest.mock import AsyncMock, Mock, patch

import pytest
from anthropic import (
    NOT_GIVEN,
    APIConnectionError,
    APITimeoutError,
    AsyncAnthropic,
    BadRequestError,
    UnprocessableEntityError,
)
from anthropic.types import (
    Completion,
    ContentBlock,
    ContentBlockDeltaEvent,
    ContentBlockStartEvent,
    ContentBlockStopEvent,
)
from anthropic.types import Message as AMessage
from anthropic.types import (
    MessageDeltaEvent,
    MessageDeltaUsage,
    MessageStartEvent,
    MessageStopEvent,
    TextDelta,
    Usage,
    message_delta_event,
)

from ai_gateway.models import (
    AnthropicAPIConnectionError,
    AnthropicAPIStatusError,
    AnthropicAPITimeoutError,
    AnthropicChatModel,
    AnthropicModel,
    KindAnthropicModel,
    Message,
    Role,
    SafetyAttributes,
    TextGenModelOutput,
)


class TestAnthropicModel:
    @pytest.mark.parametrize(
        "model_name_version",
        ["claude-instant-1.2", "claude-2.0"],
    )
    def test_anthropic_model_from_name(self, model_name_version: str):
        model = AnthropicModel.from_model_name(model_name_version, Mock())

        assert model.metadata.name == model_name_version
        assert model.metadata.engine == "anthropic"

    @pytest.mark.parametrize(
        ("model_name_version", "opts", "opts_client", "opts_model"),
        [
            (
                "claude-instant-1.2",
                {},
                AnthropicModel.OPTS_CLIENT,
                AnthropicModel.OPTS_MODEL,
            ),
            (
                "claude-instant-1.2",
                {"version": "2020-10-10"},
                AnthropicModel.OPTS_CLIENT,
                AnthropicModel.OPTS_MODEL,
            ),
            (
                "claude-instant-1.2",
                {
                    "timeout": 6,
                    "max_tokens_to_sample": 5,
                    "stop_sequences": ["\n\n"],
                    "temperature": 0.1,
                    "top_k": 40,
                    "top_p": 0.95,
                    "version": "2020-10-10",
                    "default_headers": {
                        "Custom Header": "custom",
                        "anthropic-version": "2010-10-10",
                    },
                    "max_retries": 2,
                },
                {
                    "default_headers": {
                        "Custom Header": "custom",
                        "anthropic-version": "2010-10-10",
                    },
                    "max_retries": 2,
                },
                {
                    "timeout": 6,
                    "max_tokens_to_sample": 5,
                    "stop_sequences": ["\n\n"],
                    "temperature": 0.1,
                    "top_k": 40,
                    "top_p": 0.95,
                },
            ),
        ],
    )
    def test_anthropic_provider_opts(
        self,
        model_name_version: str,
        opts: dict,
        opts_client: dict,
        opts_model: dict,
    ):
        client = Mock()
        model = AnthropicModel.from_model_name(model_name_version, client, **opts)

        headers = opts_client["default_headers"]
        if not headers.get("anthropic-version", None):
            headers["anthropic-version"] = opts.get(
                "version", AnthropicModel.DEFAULT_VERSION
            )

        client.with_options.assert_called_with(**opts_client)
        assert model.model_opts == opts_model

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("model_name_version", "exception", "expected_exception"),
        [
            ("claude-instant-1.2", BadRequestError, AnthropicAPIStatusError),
            ("claude-instant-1.2", UnprocessableEntityError, AnthropicAPIStatusError),
            ("claude-instant-1.2", APIConnectionError, AnthropicAPIConnectionError),
            ("claude-instant-1.2", APITimeoutError, AnthropicAPITimeoutError),
        ],
    )
    async def test_anthropic_model_error(
        self, model_name_version: str, exception: Type, expected_exception: Type
    ):
        def _client_predict(*_args, **_kwargs):
            if issubclass(exception, APITimeoutError):
                raise exception(request=Mock())

            if issubclass(exception, APIConnectionError):
                raise exception(message="exception", request=Mock())

            raise exception(message="exception", response=Mock(), body=Mock())

        model = AnthropicModel.from_model_name(
            model_name_version, Mock(spec=AsyncAnthropic)
        )
        model.client.completions.create = AsyncMock(side_effect=_client_predict)

        with pytest.raises(expected_exception):
            _ = await model.generate("prefix", "suffix")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        (
            "model_name_version",
            "prompt",
            "suggestion",
            "opts",
            "opts_model",
            "expected_opts_model",
            "expected_output",
        ),
        [
            (
                "claude-instant-1.2",
                "random_prompt",
                "random_text",
                {},
                {},
                {**AnthropicModel.OPTS_MODEL, **{"stream": False}},
                TextGenModelOutput(
                    text="random_text",
                    score=10_000,
                    safety_attributes=SafetyAttributes(),
                ),
            ),
            (
                "claude-instant-1.2",
                "random_prompt",
                "random_text",
                {"top_k": 10},
                {},
                {**AnthropicModel.OPTS_MODEL, **{"top_k": 10, "stream": False}},
                TextGenModelOutput(
                    text="random_text",
                    score=10_000,
                    safety_attributes=SafetyAttributes(),
                ),
            ),
            (
                "claude-instant-1.2",
                "random_prompt",
                "random_text",
                {"temperature": 1},
                {},
                {
                    **AnthropicModel.OPTS_MODEL,
                    **{"temperature": 1, "stream": False},
                },
                TextGenModelOutput(
                    text="random_text",
                    score=10_000,
                    safety_attributes=SafetyAttributes(),
                ),
            ),
            (
                "claude-instant-1.2",
                "random_prompt",
                "random_text",
                {"temperature": 1},
                {"temperature": 0.1},  # Override the temperature when calling the model
                {
                    **AnthropicModel.OPTS_MODEL,
                    **{"temperature": 0.1, "stream": False},
                },
                TextGenModelOutput(
                    text="random_text",
                    score=10_000,
                    safety_attributes=SafetyAttributes(),
                ),
            ),
            (
                "claude-instant-1.2",
                "random_prompt",
                "random_text",
                {},
                {
                    "temperature": 0.1,
                    "top_p": 0.95,
                },  # Override the temperature when calling the model
                {
                    **AnthropicModel.OPTS_MODEL,
                    **{"temperature": 0.1, "top_p": 0.95, "stream": False},
                },
                TextGenModelOutput(
                    text="random_text",
                    score=10_000,
                    safety_attributes=SafetyAttributes(),
                ),
            ),
        ],
    )
    async def test_anthropic_model_generate(
        self,
        model_name_version: str,
        prompt: str,
        suggestion: str,
        opts: dict,
        opts_model: dict,
        expected_opts_model: dict,
        expected_output: TextGenModelOutput,
    ):
        def _client_predict(*_args, **_kwargs):
            return Completion(
                id="compl_01CtvorJWMstkmATFkR7qVYM",
                completion=suggestion,
                model=model_name_version,
                stop_reason="max_tokens",
                type="completion",
            )

        model = AnthropicModel.from_model_name(
            model_name_version,
            Mock(spec=AsyncAnthropic),
            **opts,
        )

        model.client.completions.create = AsyncMock(side_effect=_client_predict)

        actual_output = await model.generate(prompt, "", **opts_model)
        # Create another dictionary to avoid modifying the original one.
        expected_opts_model = {
            **expected_opts_model,
            **{
                "model": model_name_version,
                "prompt": prompt,
            },
        }

        model.client.completions.create.assert_called_with(**expected_opts_model)
        assert actual_output.text == expected_output.text

    @pytest.mark.asyncio
    async def test_anthropic_model_generate_instrumented(self):
        model = AnthropicModel(
            model_name=KindAnthropicModel.CLAUDE_2_0.value,
            client=Mock(spec=AsyncAnthropic),
        )
        model.client.completions.create = AsyncMock()

        with patch(
            "ai_gateway.instrumentators.model_requests.ModelRequestInstrumentator.watch"
        ) as mock_watch:
            await model.generate("Wolf, what time is it?")

            mock_watch.assert_called_once_with(stream=False)

    @pytest.mark.asyncio
    async def test_anthropic_model_generate_stream_instrumented(self):
        async def mock_stream(*args, **kwargs):
            completions = [
                Completion(
                    id="compl_01CtvorJWMstkmATFkR7qVYM",
                    completion="hello",
                    model=KindAnthropicModel.CLAUDE_2_0.value,
                    stop_reason="stop_sequence",
                    type="completion",
                ),
                Completion(
                    id="compl_02CtvorJWMstkmATFkR7qVYM",
                    completion="world",
                    model=KindAnthropicModel.CLAUDE_2_0.value,
                    stop_reason="stop_sequence",
                    type="completion",
                ),
                "break here",
            ]
            for item in completions:
                if item == "break here":
                    raise ValueError("broken")
                yield item

        model = AnthropicModel(
            model_name=KindAnthropicModel.CLAUDE_2_0.value,
            client=Mock(spec=AsyncAnthropic),
        )
        model.client.completions.create = AsyncMock(side_effect=mock_stream)

        with patch(
            "ai_gateway.instrumentators.model_requests.ModelRequestInstrumentator.watch"
        ) as mock_watch:
            watcher = Mock()
            mock_watch.return_value.__enter__.return_value = watcher

            r = await model.generate("Wolf, what time is it?", stream=True)

            # Make sure we haven't called finish before completions are consumed
            watcher.finish.assert_not_called()

            with pytest.raises(ValueError):
                _ = [item async for item in r]

            mock_watch.assert_called_once_with(stream=True)
            watcher.finish.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        (
            "model_name_version",
            "prompt",
            "completion_chunks",
            "expected_chunks",
        ),
        [
            (
                "claude-instant-1.2",
                "random_prompt",
                [
                    Completion(
                        id="compl_01CtvorJWMstkmATFkR7qVYM",
                        completion="def hello_",
                        stop_reason="stop_sequence",
                        model="claude-instant-1.2",
                        type="completion",
                    ),
                    Completion(
                        id="compl_02CtvorJWMstkmATFkR7qVYM",
                        completion="world():",
                        stop_reason="stop_sequence",
                        model="claude-instant-1.2",
                        type="completion",
                    ),
                ],
                [
                    "def hello_",
                    "world():",
                ],
            ),
        ],
    )
    async def test_anthropic_model_generate_stream(
        self,
        model_name_version: str,
        prompt: str,
        completion_chunks: list[Completion],
        expected_chunks: list[str],
    ):
        async def _stream_generator(*args, **kwargs):
            for chunk in completion_chunks:
                yield chunk

        model = AnthropicModel.from_model_name(
            model_name_version,
            Mock(spec=AsyncAnthropic),
        )

        model.client.completions.create = AsyncMock(side_effect=_stream_generator)

        actual_output = await model.generate(prompt, stream=True)
        expected_opts_model = {
            **AnthropicModel.OPTS_MODEL,
            **{"model": model_name_version, "prompt": prompt, "stream": True},
        }

        chunks = []
        async for content in actual_output:
            chunks += content

        assert chunks == expected_chunks

        model.client.completions.create.assert_called_with(**expected_opts_model)


class TestAnthropicChatModel:
    @pytest.mark.parametrize(
        "model_name_version",
        [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ],
    )
    def test_anthropic_model_from_name(self, model_name_version: str):
        model = AnthropicChatModel.from_model_name(model_name_version, Mock())

        assert model.metadata.name == model_name_version
        assert model.metadata.engine == "anthropic"

    @pytest.mark.parametrize(
        ("model_name_version", "opts", "opts_client", "opts_model"),
        [
            (
                "claude-3-haiku-20240307",
                {},
                AnthropicChatModel.OPTS_CLIENT,
                AnthropicChatModel.OPTS_MODEL,
            ),
            (
                "claude-3-haiku-20240307",
                {"version": "2020-10-10"},
                AnthropicChatModel.OPTS_CLIENT,
                AnthropicChatModel.OPTS_MODEL,
            ),
            (
                "claude-3-haiku-20240307",
                {
                    "timeout": 6,
                    "max_tokens": 5,
                    "stop_sequences": ["\n\n"],
                    "temperature": 0.1,
                    "top_k": 40,
                    "top_p": 0.95,
                    "version": "2020-10-10",
                    "default_headers": {
                        "Custom Header": "custom",
                        "anthropic-version": "2010-10-10",
                    },
                    "max_retries": 2,
                },
                {
                    "default_headers": {
                        "Custom Header": "custom",
                        "anthropic-version": "2010-10-10",
                    },
                    "max_retries": 2,
                },
                {
                    "timeout": 6,
                    "max_tokens": 5,
                    "stop_sequences": ["\n\n"],
                    "temperature": 0.1,
                    "top_k": 40,
                    "top_p": 0.95,
                },
            ),
        ],
    )
    def test_anthropic_provider_opts(
        self,
        model_name_version: str,
        opts: dict,
        opts_client: dict,
        opts_model: dict,
    ):
        client = Mock()
        model = AnthropicChatModel.from_model_name(model_name_version, client, **opts)

        headers = opts_client["default_headers"]
        if not headers.get("anthropic-version", None):
            headers["anthropic-version"] = opts.get(
                "version", AnthropicChatModel.DEFAULT_VERSION
            )

        client.with_options.assert_called_with(**opts_client)
        assert model.model_opts == opts_model

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("model_name_version", "exception", "expected_exception"),
        [
            ("claude-3-haiku-20240307", BadRequestError, AnthropicAPIStatusError),
            (
                "claude-3-haiku-20240307",
                UnprocessableEntityError,
                AnthropicAPIStatusError,
            ),
            (
                "claude-3-haiku-20240307",
                APIConnectionError,
                AnthropicAPIConnectionError,
            ),
            ("claude-3-haiku-20240307", APITimeoutError, AnthropicAPITimeoutError),
        ],
    )
    async def test_anthropic_model_error(
        self, model_name_version: str, exception: Type, expected_exception: Type
    ):
        def _client_predict(*_args, **_kwargs):
            if issubclass(exception, APITimeoutError):
                raise exception(request=Mock())

            if issubclass(exception, APIConnectionError):
                raise exception(message="exception", request=Mock())

            raise exception(message="exception", response=Mock(), body=Mock())

        model = AnthropicChatModel.from_model_name(
            model_name_version, Mock(spec=AsyncAnthropic)
        )
        model.client.messages.create = AsyncMock(side_effect=_client_predict)

        with pytest.raises(expected_exception):
            _ = await model.generate(
                messages=[
                    Message(role=Role.SYSTEM, content="hello"),
                    Message(role=Role.USER, content="bye"),
                ]
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        (
            "model_name_version",
            "messages",
            "suggestion",
            "opts",
            "opts_model",
            "expected_opts_model",
            "expected_output",
        ),
        [
            (
                "claude-3-haiku-20240307",
                [
                    Message(role=Role.SYSTEM, content="nice human"),
                    Message(role=Role.USER, content="write code"),
                ],
                "random_text",
                {},
                {},
                {**AnthropicChatModel.OPTS_MODEL, **{"stream": False}},
                TextGenModelOutput(
                    text="random_text",
                    score=10_000,
                    safety_attributes=SafetyAttributes(),
                ),
            ),
            (
                "claude-3-haiku-20240307",
                [
                    Message(role=Role.SYSTEM, content="nice human"),
                    Message(role=Role.USER, content="write code"),
                ],
                "random_text",
                {"top_k": 10},
                {},
                {**AnthropicChatModel.OPTS_MODEL, **{"top_k": 10, "stream": False}},
                TextGenModelOutput(
                    text="random_text",
                    score=10_000,
                    safety_attributes=SafetyAttributes(),
                ),
            ),
            (
                "claude-3-haiku-20240307",
                [
                    Message(role=Role.SYSTEM, content="nice human"),
                    Message(role=Role.USER, content="write code"),
                ],
                "random_text",
                {"temperature": 1},
                {},
                {
                    **AnthropicChatModel.OPTS_MODEL,
                    **{"temperature": 1, "stream": False},
                },
                TextGenModelOutput(
                    text="random_text",
                    score=10_000,
                    safety_attributes=SafetyAttributes(),
                ),
            ),
            (
                "claude-3-haiku-20240307",
                [
                    Message(role=Role.USER, content="write code"),
                ],
                "random_text",
                {"temperature": 1},
                {"temperature": 0.1},  # Override the temperature when calling the model
                {
                    **AnthropicChatModel.OPTS_MODEL,
                    **{"temperature": 0.1, "stream": False},
                },
                TextGenModelOutput(
                    text="random_text",
                    score=10_000,
                    safety_attributes=SafetyAttributes(),
                ),
            ),
            (
                "claude-3-haiku-20240307",
                [
                    Message(role=Role.USER, content="write code"),
                    Message(role=Role.ASSISTANT, content="Writing code:"),
                ],
                "random_text",
                {},
                {
                    "temperature": 0.1,
                    "top_p": 0.95,
                },  # Override the temperature when calling the model
                {
                    **AnthropicChatModel.OPTS_MODEL,
                    **{"temperature": 0.1, "top_p": 0.95, "stream": False},
                },
                TextGenModelOutput(
                    text="random_text",
                    score=10_000,
                    safety_attributes=SafetyAttributes(),
                ),
            ),
        ],
    )
    async def test_anthropic_model_generate(
        self,
        model_name_version: str,
        messages: list[Message],
        suggestion: str,
        opts: dict,
        opts_model: dict,
        expected_opts_model: dict,
        expected_output: TextGenModelOutput,
    ):
        def _client_predict(*_args, **_kwargs):
            return AMessage(
                id="msg_01PE3CarfxWEG2taV9AygzH9",
                content=[ContentBlock(text=suggestion, type="text")],
                model=model_name_version,
                role="assistant",
                stop_reason="end_turn",
                stop_sequence=None,
                type="message",
                usage=Usage(input_tokens=21, output_tokens=81),
            )

        model = AnthropicChatModel.from_model_name(
            model_name_version,
            Mock(spec=AsyncAnthropic),
            **opts,
        )

        model.client.messages.create = AsyncMock(side_effect=_client_predict)

        actual_output = await model.generate(messages, **opts_model)
        # Create another dictionary to avoid modifying the original one.
        expected_opts_model = {
            **expected_opts_model,
            **{
                "model": model_name_version,
                "system": (
                    [
                        message.content
                        for message in messages
                        if message.role == Role.SYSTEM
                    ]
                    + [NOT_GIVEN]  # Use NOT_GIVEN by default
                ).pop(0),
                "messages": [
                    message.dict()
                    for message in messages
                    if message.role in (Role.USER, Role.ASSISTANT)
                ],
            },
        }

        model.client.messages.create.assert_called_with(**expected_opts_model)
        assert actual_output.text == expected_output.text

    @pytest.mark.asyncio
    async def test_anthropic_model_generate_instrumented(self):
        model = AnthropicChatModel(
            model_name=KindAnthropicModel.CLAUDE_3_HAIKU.value,
            client=Mock(spec=AsyncAnthropic),
        )
        model.client.messages.create = AsyncMock()

        with patch(
            "ai_gateway.instrumentators.model_requests.ModelRequestInstrumentator.watch"
        ) as mock_watch:
            await model.generate(
                [
                    Message(role=Role.SYSTEM, content="nice human"),
                    Message(role=Role.USER, content="write code"),
                ]
            )

            mock_watch.assert_called_once_with(stream=False)

    @pytest.mark.asyncio
    async def test_anthropic_model_generate_stream_instrumented(self):
        async def mock_stream(*args, **kwargs):
            completions = [
                MessageStartEvent(
                    message=AMessage(
                        id="msg_01PE3CarfxWEG2taV9AygzH9",
                        content=[],
                        model=KindAnthropicModel.CLAUDE_3_HAIKU.value,
                        role="assistant",
                        stop_reason=None,
                        stop_sequence=None,
                        type="message",
                        usage=Usage(input_tokens=21, output_tokens=1),
                    ),
                    type="message_start",
                ),
                ContentBlockStartEvent(
                    content_block=ContentBlock(text="", type="text"),
                    index=0,
                    type="content_block_start",
                ),
                ContentBlockDeltaEvent(
                    delta=TextDelta(text="It's", type="text_delta"),
                    index=0,
                    type="content_block_delta",
                ),
                "break here",
            ]
            for item in completions:
                if item == "break here":
                    raise ValueError("broken")
                yield item

        model = AnthropicChatModel(
            model_name=KindAnthropicModel.CLAUDE_3_HAIKU.value,
            client=Mock(spec=AsyncAnthropic),
        )
        model.client.messages.create = AsyncMock(side_effect=mock_stream)

        with patch(
            "ai_gateway.instrumentators.model_requests.ModelRequestInstrumentator.watch"
        ) as mock_watch:
            watcher = Mock()
            mock_watch.return_value.__enter__.return_value = watcher

            r = await model.generate(
                messages=[
                    Message(role=Role.SYSTEM, content="nice human"),
                    Message(role=Role.USER, content="write code"),
                ],
                stream=True,
            )

            # Make sure we haven't called finish before completions are consumed
            watcher.finish.assert_not_called()

            with pytest.raises(ValueError):
                _ = [item async for item in r]

            mock_watch.assert_called_once_with(stream=True)
            watcher.finish.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        (
            "model_name_version",
            "messages",
            "completion_chunks",
            "expected_chunks",
        ),
        [
            (
                "claude-3-haiku-20240307",
                [
                    Message(role=Role.SYSTEM, content="nice human"),
                    Message(role=Role.USER, content="write code"),
                ],
                [
                    MessageStartEvent(
                        message=AMessage(
                            id="msg_01PE3CarfxWEG2taV9AygzH9",
                            content=[],
                            model=KindAnthropicModel.CLAUDE_3_HAIKU,
                            role="assistant",
                            stop_reason=None,
                            stop_sequence=None,
                            type="message",
                            usage=Usage(input_tokens=21, output_tokens=1),
                        ),
                        type="message_start",
                    ),
                    ContentBlockStartEvent(
                        content_block=ContentBlock(text="", type="text"),
                        index=0,
                        type="content_block_start",
                    ),
                    ContentBlockDeltaEvent(
                        delta=TextDelta(text="def hello_", type="text_delta"),
                        index=0,
                        type="content_block_delta",
                    ),
                    ContentBlockDeltaEvent(
                        delta=TextDelta(text="world():", type="text_delta"),
                        index=0,
                        type="content_block_delta",
                    ),
                    ContentBlockStopEvent(index=0, type="content_block_stop"),
                    MessageDeltaEvent(
                        delta=message_delta_event.Delta(
                            stop_reason="end_turn", stop_sequence=None
                        ),
                        type="message_delta",
                        usage=MessageDeltaUsage(output_tokens=57),
                    ),
                    MessageStopEvent(type="message_stop"),
                ],
                [
                    "def hello_",
                    "world():",
                ],
            ),
        ],
    )
    async def test_anthropic_model_generate_stream(
        self,
        model_name_version: str,
        messages: list[Message],
        completion_chunks: list,
        expected_chunks: list[str],
    ):
        async def _stream_generator(*args, **kwargs):
            for chunk in completion_chunks:
                yield chunk

        model = AnthropicChatModel.from_model_name(
            model_name_version,
            Mock(spec=AsyncAnthropic),
        )

        model.client.messages.create = AsyncMock(side_effect=_stream_generator)

        actual_output = await model.generate(messages=messages, stream=True)
        expected_opts_model = {
            **AnthropicChatModel.OPTS_MODEL,
            **{
                "model": model_name_version,
                "system": "nice human",
                "messages": [{"role": Role.USER, "content": "write code"}],
                "stream": True,
            },
        }

        chunks = []
        async for content in actual_output:
            chunks += content

        assert chunks == expected_chunks

        model.client.messages.create.assert_called_with(**expected_opts_model)
