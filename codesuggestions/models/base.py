from abc import ABC, abstractmethod
from typing import NamedTuple

import numpy as np
from tritonclient.utils import np_to_triton_dtype
import tritonclient.grpc as triton_grpc_util
from google.cloud.aiplatform.gapic import PredictionServiceClient

__all__ = [
    "BaseModel",
    "TextGenModelOutput",
    "PalmTextGenBaseModel",
    "grpc_input_from_np",
    "grpc_requested_output",
    "grpc_connect_triton",
    "vertex_ai_connect",
]


class BaseModel(ABC):
    @abstractmethod
    def __call__(self, *args, **kwargs) -> str:
        pass


class TextGenModelOutput(NamedTuple):
    text: str


class PalmTextGenBaseModel(ABC):
    @abstractmethod
    def generate(
        self,
        content: str,
        temperature: float = 0.2,
        max_decode_steps: int = 16,
        top_p: float = 0.95,
        top_k: int = 40,
    ) -> TextGenModelOutput:
        pass


def grpc_input_from_np(name: str, data: np.ndarray) -> triton_grpc_util.InferInput:
    t = triton_grpc_util.InferInput(
        name, list(data.shape), np_to_triton_dtype(data.dtype)
    )
    t.set_data_from_numpy(data)
    return t


def grpc_requested_output(name: str) -> triton_grpc_util.InferRequestedOutput:
    return triton_grpc_util.InferRequestedOutput(name)


def grpc_connect_triton(host: str, port: int, verbose: bool = False) -> triton_grpc_util.InferenceServerClient:
    return triton_grpc_util.InferenceServerClient(url=f"{host}:{port}", verbose=verbose)


def vertex_ai_connect(api_endpoint: str) -> PredictionServiceClient:
    client_options = {"api_endpoint": api_endpoint}
    return PredictionServiceClient(
        client_options=client_options
    )
