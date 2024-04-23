from typing import Union, AsyncIterator, Callable, List, Dict, Optional, Any
from litellm import completion, CustomStreamWrapper

from ai_gateway.models.anthropic import KindAnthropicModel
from ai_gateway.models.base_chat import ChatModelBase, Message, Role
from ai_gateway.models.base import (
    KindModelProvider,
    ModelMetadata,
    SafetyAttributes,
    TextGenModelChunk,
    TextGenModelOutput,
    TextGenBaseModel
)
__all__ = [
    "LiteLLMChatModel",
    "LiteLlmModel"
]


class LiteLlmModel(TextGenBaseModel):
    def __init__(self,model_name: str = KindAnthropicModel.CLAUDE_2_1.value):
        self._metadata = ModelMetadata(
            name=model_name,
            engine=KindModelProvider.LITELLM.value,
        )
        self._model_name = model_name

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

        litellm_messages = self._build_messages(prefix)

        suggestion = completion(self._model_name,
                                messages=litellm_messages,
                                stream=stream)
        if stream:
            return self._handle_stream(suggestion)

        return TextGenModelOutput(
            text=suggestion.choices[0].message.content,
            # Give a high value, the model doesn't return scores.
            score=10 ** 5,
            safety_attributes=SafetyAttributes(),
        )

    def _build_messages(self, prompt: str) -> List[Dict[str, str]]:
        return [{"role": Role.USER.value, "content": prompt}]

    @staticmethod
    async def _handle_stream(
            response: CustomStreamWrapper
    ) -> AsyncIterator[TextGenModelChunk]:
        async for event in response:
            yield TextGenModelChunk(event.choices[0].delta.content or "")

    @staticmethod
    def create(model_name: str):
        return LiteLLMChatModel(model_name)


class LiteLLMChatModel(ChatModelBase):
    def __init__(self, model_name: str):
        self._metadata = ModelMetadata(
            name=model_name,
            engine=KindModelProvider.LITELLM.value,
        )
        self._model_name = model_name

    def metadata(self) -> ModelMetadata:
        return self._metadata

    async def generate(
        self,
        messages: list[Message],
        stream: bool = False,
        temperature: float = 0.2,
        max_output_tokens: int = 16,
        top_p: float = 0.95,
        top_k: int = 40,
    ) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:

        litellm_messages = self._build_messages(messages)

        suggestion = completion(self._model_name,
                                messages=litellm_messages,
                                stream=stream,
                                temperature=temperature,
                                top_p=top_p,
                                top_k=top_k,
                                max_tokens=max_output_tokens)
        if stream:
            return self._handle_stream(suggestion)

        return TextGenModelOutput(
            text=suggestion.choices[0].message.content,
            # Give a high value, the model doesn't return scores.
            score=10 ** 5,
            safety_attributes=SafetyAttributes(),
        )

    def _build_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        return [{"role": m.role.value, "content": m.content} for m in messages]

    @staticmethod
    async def _handle_stream(
            response: CustomStreamWrapper
    ) -> AsyncIterator[TextGenModelChunk]:
        async for event in response:
            yield TextGenModelChunk(event.choices[0].delta.content or "")

    @staticmethod
    def create(model_name: str):
        return LiteLLMChatModel(model_name)
