from enum import Enum
from typing import AsyncIterator, Callable, Optional, Union

from litellm import CustomStreamWrapper, acompletion

from ai_gateway.models.anthropic import KindAnthropicModel
from ai_gateway.models.base import (
    KindModelProvider,
    ModelMetadata,
    SafetyAttributes,
    TextGenModelChunk,
    TextGenModelOutput,
)
from ai_gateway.models.base_chat import ChatModelBase, Message

__all__ = [
    "LiteLlmChatModel",
    "KindSelfHostedModel",
]

STUBBED_API_KEY = "stubbed-api-key"


class KindSelfHostedModel(str, Enum):
    MISTRAL = "mistral"
    MIXTRAL = "mixtral"

    # Chat models hosted behind openai proxies should be prefixed with "openai/":
    # https://docs.litellm.ai/docs/providers/openai_compatible
    def chat_model(self) -> str:
        return "openai/" + self.value


class AllModels(Enum):
    pass


for e in KindSelfHostedModel:
    setattr(AllModels, e.name, e.value)

for e in KindAnthropicModel:
    setattr(AllModels, e.name, e.value)


class LiteLlmChatModel(ChatModelBase):
    def __init__(
        self,
        model_name: KindSelfHostedModel = KindSelfHostedModel.MISTRAL,
        model_engine: str = None,
        endpoint: Optional[str] = None,
    ):
        self.endpoint = endpoint

        if type(model_name) is KindSelfHostedModel:
            model_name = model_name.chat_model()
            model_engine = KindModelProvider.LITELLM.value
            self.options = {
                "api_key": self.api_key,
                "api_base": self.endpoint,
                "timeout": 30.0,
                "stop": ["</new_code>"],
            }
        elif type(model_name) is KindAnthropicModel:
            model_name = model_name.value
            model_engine = KindModelProvider.ANTHROPIC.value
            self.options = {}

        self._metadata = ModelMetadata(
            name=model_name,
            engine=model_engine,
        )

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
                **self.options,
            )

            if stream:
                return self._handle_stream(
                    suggestion,
                    lambda: watcher.finish(),
                    lambda: watcher.register_error(),
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
        name: Union[str, KindSelfHostedModel, KindAnthropicModel],
        endpoint: Optional[str] = None,
    ):
        try:
            model_name = KindSelfHostedModel(name)
        except ValueError:
            pass

        try:
            model_name = KindAnthropicModel(name)
        except ValueError:
            pass

        if model_name is None:
            raise ValueError(f"no model found by the name '{name}'")

        return cls(model_name=model_name, endpoint=endpoint)
