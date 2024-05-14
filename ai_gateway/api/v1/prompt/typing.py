from typing import Optional
from pydantic import BaseModel
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


class RawRequestBody(BaseModel):
    variables: dict
    prompt: str


class PromptResponse(BaseModel):
    prompt_name: str
    prompt_version: str
    response: str


class RawResponse(BaseModel):
    response: str
