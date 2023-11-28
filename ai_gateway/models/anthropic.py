from typing import Any, AsyncIterator, Optional, Union

import httpx
import structlog
from anthropic import (
    APIConnectionError,
    APIError,
    APIStatusError,
    AsyncAnthropic,
    AsyncStream,
)
from anthropic._types import NOT_GIVEN

from ai_gateway.models.base import (
    ModelAPICallError,
    ModelAPIError,
    ModelMetadata,
    SafetyAttributes,
    TextGenBaseModel,
    TextGenModelChunk,
    TextGenModelOutput,
)

__all__ = [
    "AnthropicAPIConnectionError",
    "AnthropicAPIStatusError",
    "AnthropicModel",
]

log = structlog.stdlib.get_logger("codesuggestions")


class AnthropicAPIConnectionError(ModelAPIError):
    @classmethod
    def from_exception(cls, ex: APIError):
        wrapper = cls(ex.message, errors=(ex,))

        return wrapper


class AnthropicAPIStatusError(ModelAPICallError):
    @classmethod
    def from_exception(cls, ex: APIStatusError):
        cls.code = ex.status_code
        wrapper = cls(ex.message, errors=(ex,))

        return wrapper


class AnthropicModel(TextGenBaseModel):
    # Ref: https://docs.anthropic.com/claude/reference/selecting-a-model
    MAX_MODEL_LEN = 100_000
    CLAUDE_INSTANT = "claude-instant-1.2"
    CLAUDE = "claude-2.0"

    # Ref: https://docs.anthropic.com/claude/reference/versioning
    DEFAULT_VERSION = "2023-06-01"

    MODEL_ENGINE = "anthropic"

    OPTS_CLIENT = {
        "default_headers": {},
        "max_retries": 1,
    }

    OPTS_MODEL = {
        "timeout": httpx.Timeout(600.0, connect=5.0),
        "max_tokens_to_sample": 2048,
        "stop_sequences": NOT_GIVEN,
        "temperature": 0.2,
        "top_k": NOT_GIVEN,
        "top_p": NOT_GIVEN,
    }

    def __init__(
        self,
        model_name: str,
        client: AsyncAnthropic,
        version: str = DEFAULT_VERSION,
        **kwargs: Any,
    ):
        client_opts = self._obtain_client_opts(version, **kwargs)
        self.client = client.with_options(**client_opts)
        self.model_opts = self._obtain_model_opts(**kwargs)

        self._metadata = ModelMetadata(
            name=model_name,
            engine=AnthropicModel.MODEL_ENGINE,
        )

    @staticmethod
    def _obtain_model_opts(**kwargs: Any):
        return _obtain_opts(AnthropicModel.OPTS_MODEL, **kwargs)

    @staticmethod
    def _obtain_client_opts(version: str, **kwargs: Any):
        opts = _obtain_opts(AnthropicModel.OPTS_CLIENT, **kwargs)

        headers = opts["default_headers"]
        if not headers.get("anthropic-version", None):
            headers["anthropic-version"] = version

        return opts

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    async def generate(
        self,
        prefix: str,
        _suffix: Optional[str] = "",
        stream: bool = False,
        **kwargs: Any,
    ) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:
        opts = _obtain_opts(self.model_opts, **kwargs)
        log.debug("codegen anthropic call:", **opts)

        try:
            suggestion = await self.client.completions.create(
                model=self.metadata.name,
                prompt=prefix,
                stream=stream,
                **opts,
            )
        except APIStatusError as ex:
            raise AnthropicAPIStatusError.from_exception(ex)
        except APIConnectionError as ex:
            raise AnthropicAPIConnectionError.from_exception(ex)

        if stream:
            return self._handle_stream(suggestion)

        return TextGenModelOutput(
            text=suggestion.completion,
            # Give a high value, the model doesn't return scores.
            score=10**5,
            safety_attributes=SafetyAttributes(),
        )

    async def _handle_stream(
        self, response: AsyncStream
    ) -> AsyncIterator[TextGenModelChunk]:
        async for event in response:
            chunk_content = TextGenModelChunk(text=event.completion)
            yield chunk_content

    @classmethod
    def from_model_name(cls, name: str, client: AsyncAnthropic, **kwargs: Any):
        if not name.startswith((cls.CLAUDE_INSTANT, cls.CLAUDE)):
            raise ValueError(f"no model found by the name '{name}'")

        return cls(name, client, **kwargs)


def _obtain_opts(default_opts: dict, **kwargs: Any) -> dict:
    return {
        opt_name: kwargs.pop(opt_name, opt_value) or opt_value
        for opt_name, opt_value in default_opts.items()
    }
