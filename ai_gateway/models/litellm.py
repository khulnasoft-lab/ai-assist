from enum import Enum
from typing import AsyncIterator, Callable, Optional, Union

from litellm import CustomStreamWrapper, acompletion

from ai_gateway.models.base import KindModelProvider, ModelMetadata, SafetyAttributes
from ai_gateway.models.base_chat import ChatModelBase, Message, Role
from ai_gateway.models.base_text import (
    TextGenModelBase,
    TextGenModelChunk,
    TextGenModelOutput,
)

__all__ = [
    "LiteLlmChatModel",
    "LiteLlmTextGenModel",
    "KindLiteLlmModel",
]

STUBBED_API_KEY = "stubbed-api-key"


class KindLiteLlmModel(str, Enum):
    MISTRAL = "mistral"
    MIXTRAL = "mixtral"
    CODE_GEMMA = "codegemma"
    CODESTRAL = "codestral"
    CODE_LLAMA = "codellama"

    # Chat models hosted behind openai proxies should be prefixed with "openai/":
    # https://docs.litellm.ai/docs/providers/openai_compatible
    def chat_model(self) -> str:
        return "openai/" + self.value

    # Text completion models hosted behind openai proxies should be prefixed with "text-completion-openai/":
    # https://docs.litellm.ai/docs/providers/openai_compatible
    def text_model(self) -> str:
        return "text-completion-openai/" + self.value


MODEL_STOP_TOKENS = {
    KindLiteLlmModel.MISTRAL: ["</new_code>"],
    KindLiteLlmModel.MIXTRAL: ["</new_code>"],
    # Ref: https://huggingface.co/google/codegemma-7b
    # The model returns the completion, followed by one of the FIM tokens or the EOS token.
    # You should ignore everything that comes after any of these tokens.
    KindLiteLlmModel.CODE_GEMMA: [
        "<|fim_prefix|>",
        "<|fim_suffix|>",
        "<|fim_middle|>",
        "<|file_separator|>",
    ],
}


class LiteLlmChatModel(ChatModelBase):
    def __init__(
        self,
        model_name: KindLiteLlmModel = KindLiteLlmModel.MISTRAL,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        if api_key is None:
            api_key = STUBBED_API_KEY

        self.api_key = api_key
        self.endpoint = endpoint
        self._metadata = ModelMetadata(
            name=model_name.chat_model(),
            engine=KindModelProvider.LITELLM.value,
        )
        self.stop_tokens = MODEL_STOP_TOKENS.get(model_name, [])

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    async def generate(
        self,
        messages: list[Message],
        stream: bool = False,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
        top_p: float = 0.95,
        top_k: int = 40,
    ) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:

        if isinstance(messages, str):
            messages = [Message(content=messages, role=Role.USER)]

        litellm_messages = [message.model_dump(mode="json") for message in messages]

        with self.instrumentator.watch(stream=stream) as watcher:
            suggestion = await acompletion(
                self.metadata.name,
                messages=litellm_messages,
                stream=stream,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_output_tokens,
                api_key=self.api_key,
                api_base=self.endpoint,
                timeout=30.0,
                stop=self.stop_tokens,
            )

            if stream:
                return self._handle_stream(
                    suggestion,
                    watcher.finish,
                    watcher.register_error,
                )

        return TextGenModelOutput(
            text=suggestion.choices[0].message.content,
            # Give a high value, the model doesn't return scores.
            score=10**5,
            safety_attributes=SafetyAttributes(),
        )

    async def _handle_stream(
        self,
        response: CustomStreamWrapper,
        after_callback: Callable,
        error_callback: Callable,
    ) -> AsyncIterator[TextGenModelChunk]:
        try:
            async for chunk in response:
                yield TextGenModelChunk(text=(chunk.choices[0].delta.content or ""))
        except Exception:
            error_callback()
            raise
        finally:
            after_callback()

    @classmethod
    def from_model_name(
        cls,
        name: Union[str, KindLiteLlmModel],
        custom_models_enabled: bool = False,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        if not custom_models_enabled:
            if endpoint is not None or api_key is not None:
                raise ValueError("specifying custom models endpoint is disabled")

        try:
            kind_model = KindLiteLlmModel(name)
        except ValueError:
            raise ValueError(f"no model found by the name '{name}'")

        return cls(model_name=kind_model, endpoint=endpoint, api_key=api_key)


class LiteLlmTextGenModel(TextGenModelBase):
    def __init__(
        self,
        model_name: KindLiteLlmModel = KindLiteLlmModel.CODE_GEMMA,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        if api_key is None:
            api_key = STUBBED_API_KEY

        self.api_key = api_key
        self.endpoint = endpoint
        self._metadata = ModelMetadata(
            name=model_name.text_model(),
            engine=KindModelProvider.LITELLM.value,
        )
        self.stop_tokens = MODEL_STOP_TOKENS.get(model_name, [])

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    async def generate(
        self,
        prefix: str,
        _suffix: Optional[str] = "",
        stream: bool = False,
        temperature: float = 0.95,
        max_output_tokens: int = 16,
        top_p: float = 0.95,
        top_k: int = 40,
    ) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:

        with self.instrumentator.watch(stream=stream) as watcher:
            suggestion = await acompletion(
                model=self.metadata.name,
                messages=[{"content": prefix, "role": Role.USER}],
                max_tokens=max_output_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=stream,
                api_key=self.api_key,
                api_base=self.endpoint,
                timeout=30.0,
                stop=self.stop_tokens,
            )

            if stream:
                return self._handle_stream(
                    suggestion,
                    watcher.finish,
                    watcher.register_error,
                )

        return TextGenModelOutput(
            text=suggestion.choices[0].message.content,
            # Give a high value, the model doesn't return scores.
            score=10**5,
            safety_attributes=SafetyAttributes(),
        )

    async def _handle_stream(
        self,
        response: CustomStreamWrapper,
        after_callback: Callable,
        error_callback: Callable,
    ) -> AsyncIterator[TextGenModelChunk]:
        try:
            async for chunk in response:
                yield TextGenModelChunk(text=(chunk.choices[0].delta.content or ""))
        except Exception:
            error_callback()
            raise
        finally:
            after_callback()

    @classmethod
    def from_model_name(
        cls,
        name: Union[str, KindLiteLlmModel],
        custom_models_enabled: bool = False,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        if not custom_models_enabled:
            if endpoint is not None or api_key is not None:
                raise ValueError("specifying custom models endpoint is disabled")

        try:
            kind_model = KindLiteLlmModel(name)
        except ValueError:
            raise ValueError(f"no model found by the name '{name}'")

        return cls(model_name=kind_model, endpoint=endpoint, api_key=api_key)
