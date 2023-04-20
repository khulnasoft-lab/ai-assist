from typing import Dict, Optional

from google.cloud.aiplatform.gapic import PredictionServiceClient, PredictResponse
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value

from codesuggestions.models import PalmTextGenBaseModel, TextGenModelOutput


__all__ = [
    "PalmTextGenModel",
]


class PalmTextGenModel(PalmTextGenBaseModel):
    def __init__(self, client: PredictionServiceClient, project: str, location: str, endpoint_id: str):
        self.client = client
        self.project = project
        self.location = location
        self.endpoint_id = endpoint_id

    def _request_predictions(self, instance: Dict, parameters: Dict, timeout: float) -> PredictResponse:
        instance_pb = json_format.ParseDict(instance, Value())
        parameters_pb = json_format.ParseDict(parameters, Value())

        endpoint = self.client.endpoint_path(
            project=self.project, location=self.location, endpoint=self.endpoint_id
        )
        response = self.client.predict(
            endpoint=endpoint, instances=[instance_pb], parameters=parameters_pb, timeout=timeout,
        )

        return response

    def generate(
        self,
        content: str,
        temperature: float = 0.2,
        max_decode_steps: int = 16,
        top_p: float = 0.95,
        top_k: int = 40,
        timeout: float = 10,
    ) -> Optional[TextGenModelOutput]:
        instance = {
            "content": content
        }
        parameters = {
            "temperature": temperature,
            "maxDecodeSteps": max_decode_steps,
            "topP": top_p,
            "topK": top_k,
        }

        response = self._request_predictions(instance, parameters, timeout)
        if len(response.predictions) > 0:
            prediction = response.predictions.pop()
            content = prediction["content"]

            return TextGenModelOutput(
                text=content,
            )

        return None
