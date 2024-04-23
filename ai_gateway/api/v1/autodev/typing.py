from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints, field_validator
from pydantic.types import Json

from ai_gateway.models import KindAnthropicModel, KindModelProvider

__all__ = [
    "AutodevRequest",
    "AutodevResponse",
]

class AutodevRequest(BaseModel):
    issue_id: int
    project_id: int
    instance_url: str

class AutodevResponse(BaseModel):
    response: str
