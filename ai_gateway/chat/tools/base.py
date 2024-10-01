from abc import ABC
from typing import Any, Optional

from pydantic import BaseModel

__all__ = [
    "BaseTool",
    "BaseRemoteTool",
]


class BaseToolParameter(ABC, BaseModel, frozen=True):
    name: str
    description: str
    required: bool = False
    type: str


class BaseTool(ABC, BaseModel, frozen=True):
    name: str
    description: str
    resource: Optional[str] = None
    example: Optional[str] = None
    parameters: Optional[list[BaseToolParameter]] = None


class BaseRemoteTool(BaseTool):
    def _run(self, *args: Any, **kwargs: Any) -> Any:
        # By default, we run tools on the Ruby app side
        raise NotImplementedError(
            "Please check the Rails app for an implementation of this tool."
        )
