from typing import Optional, List
from pydantic import BaseModel, Json
from fastapi import Request
__all__ = [
    "PromptRequestBody",
    "PromptResponse"
]


class PromptRequest(Request):
    prompt_name: str
    prompt_version: str


class PromptRequestBody(BaseModel):
    variables: dict


class PromptResponse(BaseModel):
    prompt_name: str
    prompt_version: str
    response: str


class RawResponse(BaseModel):
    response: str


class PromptPayload(BaseModel):
    content: str
    variables: Optional[Json] = {}


class PromptMetadata(BaseModel):
    source: str
    version: str


class PromptComponent(BaseModel):
    type: str
    metadata: PromptMetadata
    payload: PromptPayload


class RawRequestBody(BaseModel):
    prompt_components: List[PromptComponent]
    stream: Optional[bool] = False
