from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, NamedTuple, Union

import httpx
from anthropic import AsyncAnthropic
from google.cloud.aiplatform.gapic import PredictionServiceAsyncClient
from pydantic import BaseModel

__all__ = [
    "ModelAPIError",
    "ModelAPICallError",
    "ModelMetadata",
    "SafetyAttributes",
    "TextGenModelOutput",
    "TextGenModelChunk",
    "TextGenBaseModel",
    "grpc_connect_vertex",
    "connect_anthropic",
    "connect_chat_anthropic",
]


class ModelAPIError(Exception):
    def __init__(self, message: str, errors: tuple = (), details: tuple = ()):
        self.message = message
        self._errors = errors
        self._details = details

    def __str__(self):
        message = self.message

        if self.details:
            message = f"{message} {', '.join(self.details)}"

        return message

    @property
    def errors(self) -> list[Any]:
        return list(self._errors)

    @property
    def details(self) -> list[Any]:
        return list(self._details)


class ModelAPICallError(ModelAPIError):
    code: int

    def __init__(self, message: str, errors: tuple = (), details: tuple = ()):
        super().__init__(f"{self.code} {message}", errors=errors, details=details)


class ModelMetadata(NamedTuple):
    name: str
    engine: str


class ModelInput(ABC):
    @abstractmethod
    def is_valid(self) -> bool:
        pass

    @abstractmethod
    def dict(self) -> dict:
        pass

    def __eq__(self, obj):
        return self.dict() == obj.dict()


class SafetyAttributes(BaseModel):
    blocked: bool = False
    categories: list[str] = []
    errors: list[int] = []


class TextGenModelOutput(NamedTuple):
    text: str
    score: float
    safety_attributes: SafetyAttributes


class TextGenModelChunk(NamedTuple):
    text: str


class TextGenBaseModel(ABC):
    MAX_MODEL_LEN = 2048

    @property
    @abstractmethod
    def metadata(self) -> ModelMetadata:
        pass

    @abstractmethod
    async def generate(
        self,
        prefix: str,
        suffix: str,
        stream: bool = False,
        temperature: float = 0.2,
        max_output_tokens: int = 16,
        top_p: float = 0.95,
        top_k: int = 40,
    ) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:
        pass


def grpc_connect_vertex(client_options: dict) -> PredictionServiceAsyncClient:
    return PredictionServiceAsyncClient(client_options=client_options)


def connect_anthropic(**kwargs: Any) -> AsyncAnthropic:
    return AsyncAnthropic(**kwargs)


def connect_chat_anthropic() -> AsyncAnthropic:
    return AsyncAnthropic(
        timeout=httpx.Timeout(30.0, connect=5.0),
        max_retries=1,
    )
