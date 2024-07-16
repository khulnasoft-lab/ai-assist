from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel

from ai_gateway.auth import GitLabUser
from ai_gateway.chat.tools import BaseTool
from ai_gateway.cloud_connector.unit_primitive import GitLabUnitPrimitive

__all__ = [
    "UnitPrimitiveToolset",
    "BaseToolsRegistry",
]


class UnitPrimitiveToolset(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    name: GitLabUnitPrimitive
    tools: list[BaseTool]

    # Minimum required GitLab version to use the tools.
    # If it's not set, the tools are available for all GitLab versions.
    min_required_gl_version: Optional[str] = None


class BaseToolsRegistry(ABC):
    @abstractmethod
    def get_on_behalf(self, user: GitLabUser) -> list[BaseTool]:
        pass

    @abstractmethod
    def get_all(self) -> list[BaseTool]:
        pass
