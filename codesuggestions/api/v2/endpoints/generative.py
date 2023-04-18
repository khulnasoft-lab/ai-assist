import uuid
from time import time
from typing import Literal

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from pydantic import BaseModel, constr, Field


__all__ = [
    "router",
]

router = APIRouter(
    prefix="/generate",
    tags=["Generative API"],
)


class PalmTextModelInput(BaseModel):
    name: Literal["text-bison-001"]
    content: str = constr(max_length=100000)
    temperature: float = Field(0.2, ge=0, le=1)
    max_decode_steps: int = Field(16, ge=1, le=1024)
    top_p: float = Field(0.95, ge=0, le=1)
    top_k: int = Field(40, ge=1, le=40)


class PalmTextModelOutput(BaseModel):
    class Choice(BaseModel):
        text: str
        index: int = 0
        finish_reason: str = "length"

    name: str
    choices: list[Choice]


class PalmGenerativeRequest(BaseModel):
    prompt_version: int = 1
    model: PalmTextModelInput


class PalmGenerativeResponse(BaseModel):
    id: str
    objective: str
    created: int
    model: PalmTextModelOutput


@router.post("/palm", response_model=PalmGenerativeResponse)
async def palm(
    req: PalmGenerativeRequest,
):
    return PalmGenerativeResponse(
        id=uuid.uuid4().hex,
        created=int(time()),
    )
