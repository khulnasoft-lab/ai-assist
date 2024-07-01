from enum import Enum
from typing import AsyncIterator, Callable, Optional, Union

from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatCompletionStreamResponse

from ai_gateway.models.base import KindModelProvider, ModelMetadata, SafetyAttributes
from ai_gateway.models.base_chat import ChatModelBase, Message, Role
from ai_gateway.models.base_text import (
    TextGenModelBase,
    TextGenModelChunk,
    TextGenModelOutput,
)

__all__ = [
    "MistralChatModel",
    "MistralTextGenModel",
    "KindMistralModel",
]

STUBBED_API_KEY = "stubbed-api-key"


class KindMistralModel(str, Enum):
    MISTRAL = "mistral"
    MIXTRAL = "mixtral"
    CODESTRAL = "codestral-latest"


MODEL_STOP_TOKENS = {
    KindMistralModel.MISTRAL: ["</new_code>"],
    KindMistralModel.MIXTRAL: ["</new_code>"],
    KindMistralModel.CODESTRAL: ["[INST]", "[PREFIX]", "[SUFFIX]", "[MIDDLE]"],
}


class MistralChatModel(ChatModelBase):
    def __init__(
        self,
        client: MistralClient,
        model_name: KindMistralModel = KindMistralModel.MISTRAL,
        api_key: Optional[str] = None,
    ):
        if api_key is None:
            api_key = STUBBED_API_KEY

        self.api_key = api_key
        self.client = client
        self._metadata = ModelMetadata(
            name=model_name.value,
            engine=KindModelProvider.MISTRAL.value,
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

        mistral_messages = [message.model_dump(mode="json") for message in messages]

        with self.instrumentator.watch(stream=stream) as watcher:
            completion_func = (
                self.client.completion_stream if stream else self.client.completion
            )
            suggestion = completion_func(
                model=self.metadata.name,
                messages=mistral_messages,
                stream=stream,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_output_tokens,
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
        response: ChatCompletionStreamResponse,
        after_callback: Callable,
        error_callback: Callable,
    ) -> AsyncIterator[TextGenModelChunk]:
        try:
            for chunk in response:
                yield TextGenModelChunk(text=(chunk.choices[0].delta.content or ""))
        except Exception:
            error_callback()
            raise
        finally:
            after_callback()

    @classmethod
    def from_model_name(
        cls,
        name: Union[str, KindMistralModel],
        client: MistralClient,
        api_key: Optional[str] = None,
    ):
        try:
            kind_model = KindMistralModel(name)
        except ValueError:
            raise ValueError(f"no model found by the name '{name}'")

        return cls(model_name=kind_model, api_key=api_key, client=client)


class MistralTextGenModel(TextGenModelBase):
    def __init__(
        self,
        client: MistralClient,
        model_name: KindMistralModel = KindMistralModel.CODESTRAL,
        api_key: Optional[str] = None,
    ):
        if api_key is None:
            api_key = STUBBED_API_KEY

        self.api_key = api_key
        self.client = client
        self._metadata = ModelMetadata(
            name=model_name,
            engine=KindModelProvider.MISTRAL.value,
        )
        self.stop_tokens = MODEL_STOP_TOKENS.get(model_name, [])

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    async def generate(
        self,
        prefix: str,
        suffix: Optional[str] = "",
        stream: bool = False,
        temperature: float = 0.95,
        max_output_tokens: int = 16,
        top_p: float = 0.95,
        top_k: int = 40,
    ) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:

        with self.instrumentator.watch(stream=stream) as watcher:
            completion_func = (
                self.client.completion_stream if stream else self.client.completion
            )
            suggestion = completion_func(
                model=self.metadata.name,
                prompt=prefix,
                suffix=suffix,
                max_tokens=max_output_tokens,
                temperature=temperature,
                top_p=top_p,
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
        response: ChatCompletionStreamResponse,
        after_callback: Callable,
        error_callback: Callable,
    ) -> AsyncIterator[TextGenModelChunk]:
        try:
            for chunk in response:
                yield TextGenModelChunk(text=(chunk.choices[0].delta.content or ""))
        except Exception:
            error_callback()
            raise
        finally:
            after_callback()

    @classmethod
    def from_model_name(
        cls,
        name: Union[str, KindMistralModel],
        client: MistralClient,
        api_key: Optional[str] = None,
    ):
        try:
            kind_model = KindMistralModel(name)
        except ValueError:
            raise ValueError(f"no model found by the name '{name}'")

        return cls(model_name=kind_model, api_key=api_key, client=client)
