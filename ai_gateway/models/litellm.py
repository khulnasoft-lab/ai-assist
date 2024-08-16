from enum import Enum
from typing import AsyncIterator, Callable, Optional, Sequence, Union

from litellm import CustomStreamWrapper, acompletion, atext_completion

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
    CODE_GEMMA = "codegemma"
    CODE_LLAMA = "codellama"
    CODE_LLAMA_CODE = "codellama:code"
    CODESTRAL = "codestral"
    DEEPSEEKCODER = "deepseekcoder"
    MISTRAL = "mistral"
    MIXTRAL = "mixtral"
    CODESTRAL_2405 = "codestral@2405"

    def _chat_provider_prefix(self, provider):
        # Chat models hosted behind openai proxies should be prefixed with "openai/":
        # https://docs.litellm.ai/docs/providers/openai_compatible
        if provider == KindModelProvider.LITELLM:
            return "openai"

        return provider.value

    def _text_provider_prefix(self, provider):
        # KindModelProvider.VERTEX_AI is 'vertex-ai', whereas LiteLLM uses 'vertex_ai' as the key for Vertex provider
        # We need to transform the provider prefix to what's compatible with LiteLLM
        if provider == KindModelProvider.VERTEX_AI:
            return "vertex_ai"

        # Text completion models hosted behind openai proxies should be prefixed with "text-completion-openai/":
        # https://docs.litellm.ai/docs/providers/openai_compatible
        if provider == KindModelProvider.LITELLM:
            return "text-completion-openai"

        return f"text-completion-{provider.value}"

    def chat_model(self, provider=KindModelProvider.LITELLM) -> str:
        return f"{self._chat_provider_prefix(provider)}/{self.value}"

    def text_model(self, provider=KindModelProvider.LITELLM) -> str:
        return f"{self._text_provider_prefix(provider)}/{self.value}"


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

MODEL_SPECIFICATIONS = {
    KindLiteLlmModel.CODESTRAL_2405: {
        "stop": [
            "[INST]",
            "[/INST]",
            "[PREFIX]",
            "[MIDDLE]",
            "[SUFFIX]",
        ],
        "temperature": 0.7,
        "max_tokens": 128,
        "timeout": 60,
        "vertex_location": "us-central1",
    }
}


class LiteLlmChatModel(ChatModelBase):
    @property
    def MAX_MODEL_LEN(self):  # pylint: disable=invalid-name
        if self._metadata.name == KindLiteLlmModel.CODE_GEMMA:
            return 8_192

        if self._metadata.name in (
            KindLiteLlmModel.CODE_LLAMA,
            KindLiteLlmModel.CODE_LLAMA_CODE,
        ):
            return 16_384

        return 32_768

    def __init__(
        self,
        model_name: KindLiteLlmModel = KindLiteLlmModel.MISTRAL,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        provider: Optional[KindModelProvider] = KindModelProvider.LITELLM,
    ):
        if not api_key:
            api_key = STUBBED_API_KEY

        self.api_key = api_key
        self.endpoint = endpoint
        self.provider = provider
        self._metadata = ModelMetadata(
            name=model_name.chat_model(provider),
            engine=provider.value,
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
        code_context: Optional[Sequence[str]] = None,
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
        provider: Optional[KindModelProvider] = KindModelProvider.LITELLM,
        provider_keys: Optional[dict] = None,
    ):
        if not custom_models_enabled and provider == KindModelProvider.LITELLM:
            if endpoint is not None or api_key is not None:
                raise ValueError("specifying custom models endpoint is disabled")

        if provider == KindModelProvider.MISTRALAI:
            api_key = provider_keys.get("mistral_api_key")

        try:
            kind_model = KindLiteLlmModel(name)
        except ValueError:
            raise ValueError(f"no model found by the name '{name}'")

        return cls(
            model_name=kind_model, endpoint=endpoint, api_key=api_key, provider=provider
        )


class LiteLlmTextGenModel(TextGenModelBase):
    @property
    def MAX_MODEL_LEN(self):  # pylint: disable=invalid-name
        if self._metadata.name == KindLiteLlmModel.CODE_GEMMA:
            return 8_192

        if self._metadata.name in (
            KindLiteLlmModel.CODE_LLAMA,
            KindLiteLlmModel.CODE_LLAMA_CODE,
        ):
            return 16_384

        return 32_768

    def __init__(
        self,
        model_name: KindLiteLlmModel = KindLiteLlmModel.CODE_GEMMA,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        provider: Optional[KindModelProvider] = KindModelProvider.LITELLM,
    ):
        if not api_key:
            api_key = STUBBED_API_KEY

        self.api_key = api_key
        self.endpoint = endpoint
        self.provider = provider
        self.model_name = model_name
        self._metadata = ModelMetadata(
            name=model_name.text_model(provider),
            engine=provider.value,
        )
        self.stop_tokens = MODEL_STOP_TOKENS.get(model_name, [])

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    @property
    def specifications(self):
        return MODEL_SPECIFICATIONS.get(self.model_name, {})

    async def generate(
        self,
        prefix: str,
        suffix: Optional[str] = "",
        stream: bool = False,
        temperature: float = 0.95,
        max_output_tokens: int = 16,
        top_p: float = 0.95,
        top_k: int = 40,
        code_context: Optional[Sequence[str]] = None,
    ) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:

        with self.instrumentator.watch(stream=stream) as watcher:
            suggestion = await self._get_suggestion(
                prefix=prefix,
                suffix=suffix,
                stream=stream,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                top_p=top_p,
            )

            if stream:
                return self._handle_stream(
                    suggestion,
                    watcher.finish,
                    watcher.register_error,
                )

        return TextGenModelOutput(
            text=self._extract_suggestion_text(suggestion),
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

    async def _get_suggestion(
        self,
        prefix: str,
        suffix: str,
        stream: bool,
        temperature: float,
        max_output_tokens: int,
        top_p: float,
    ):
        completion_args = {
            "model": self.metadata.name,
            "messages": [{"content": prefix, "role": Role.USER}],
            "max_tokens": self.specifications.get("max_tokens", max_output_tokens),
            "temperature": self.specifications.get("temperature", temperature),
            "top_p": top_p,
            "stream": stream,
            "timeout": self.specifications.get("timeout", 30.0),
            "stop": self.specifications.get("stop", self.stop_tokens),
        }

        if self._is_vertex():
            completion_args["vertex_ai_location"] = self.specifications.get(
                "vertex_location"
            )
        else:
            completion_args["api_key"] = self.api_key
            completion_args["api_base"] = self.endpoint

        if self._use_text_completion():
            completion_args["suffix"] = suffix
            return await atext_completion(**completion_args)

        return await acompletion(**completion_args)

    def _is_vertex(self):
        return self.provider == KindModelProvider.VERTEX_AI

    def _use_text_completion(self):
        return self._is_vertex and self.model_name == KindLiteLlmModel.CODESTRAL_2405

    def _extract_suggestion_text(self, suggestion):
        if self._use_text_completion():
            return suggestion.choices[0].text

        return suggestion.choices[0].message.content

    @classmethod
    def from_model_name(
        cls,
        name: Union[str, KindLiteLlmModel],
        custom_models_enabled: bool = False,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        provider: Optional[KindModelProvider] = KindModelProvider.LITELLM,
        provider_keys: Optional[dict] = None,
    ):
        if endpoint is not None or api_key is not None:
            if not custom_models_enabled and provider == KindModelProvider.LITELLM:
                raise ValueError("specifying custom models endpoint is disabled")
            if provider == KindModelProvider.VERTEX_AI:
                raise ValueError(
                    "specifying api endpoint or key for vertex-ai provider is disabled"
                )

        if provider == KindModelProvider.MISTRALAI:
            api_key = provider_keys.get("mistral_api_key")

        try:
            kind_model = KindLiteLlmModel(name)
        except ValueError:
            raise ValueError(f"no model found by the name '{name}'")

        return cls(
            model_name=kind_model, endpoint=endpoint, api_key=api_key, provider=provider
        )
