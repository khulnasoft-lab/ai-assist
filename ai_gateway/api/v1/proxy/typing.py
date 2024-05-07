from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field, StringConstraints


class LiteLlmRequestMessage(BaseModel):
    content: str
    role: str


class LiteLlmRequest(BaseModel):
    model: str
    messages: list[LiteLlmRequestMessage]
    stream: Optional[bool] = False
