from typing import Any, Optional, Sequence, Union, Callable, AsyncIterator
from enum import Enum
import httpx
import json

from ai_gateway.models.base import (
    KindModelProvider,
    ModelInput,
    ModelMetadata,
    SafetyAttributes,
    TextGenBaseModel,
    TextGenModelOutput,
    TextGenModelChunk
)

class KindCustomModel(str, Enum):
    pass

class CustomModelInput(ModelInput):
    def __init__(self, model_name: str, prompt: str, stream: bool):
        self.prompt = prompt
        self.model_name = model_name
        self.stream = stream

    def is_valid(self) -> bool:
        return len(self.prompt) > 0 and self.model_name is not None

    def dict(self) -> dict:
        return {
            "model": self.model_name,
            "prompt": self.prompt,
            "stream": self.stream
        }

class CustomModel(TextGenBaseModel):
    def __init__(self, client: httpx.AsyncClient, model_name: str, prompt_template: str, url: str):
        self.client = client
        self.url = url
        self.model_name = model_name
        self.prompt_template = prompt_template
        self._metadata = ModelMetadata(
            name=model_name, engine=KindModelProvider.CUSTOM
        )

    async def generate(
        self,
        prefix: str,
        suffix: str,
        stream: bool = False,
        temperature: float = 0.2,
        max_output_tokens: int = 64,
        top_p: float = 0.95,
        top_k: int = 40,
        stop_sequences: Optional[Sequence[str]] = None,
    ) -> Optional[TextGenModelOutput]:
        
        template_inputs = {
            "prefix": prefix,
            "suffix": suffix
        }
        prompt = self.prompt_template.format(**template_inputs)

        model_input = CustomModelInput(
            model_name=self.model_name,
            prompt=prompt,
            stream=stream
        )

        req = self.client.build_request("POST", self.url, json=model_input.dict(), timeout=None)

        with self.instrumentator.watch(stream=stream) as watcher:
            suggestion = await self.client.send(req, stream=stream)

            if stream:
                return self._handle_stream(suggestion, lambda: watcher.finish())

        return TextGenModelOutput(
            text=suggestion.json()['response'],
            score=10**5,
            safety_attributes=SafetyAttributes(),
        )
    
    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata
    
    @classmethod
    def from_model_name(
        cls, name: Union[str, KindCustomModel], **kwargs: Any
    ):
        return cls(model_name=name, **kwargs)
    
    async def _handle_stream(
        self, response: httpx.Response, after_callback: Callable
    ) -> AsyncIterator[TextGenModelChunk]:
        try:
            async for event in response.aiter_text():
                data = json.loads(event)['response']
                chunk_content = TextGenModelChunk(text=data)
                yield chunk_content
        finally:
            after_callback()