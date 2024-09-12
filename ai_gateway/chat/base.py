from abc import ABC, abstractmethod
from typing import Optional

from packaging.version import InvalidVersion, Version
from pydantic import BaseModel

from ai_gateway.auth import GitLabUser
from ai_gateway.chat.tools import BaseTool
from ai_gateway.gitlab_features import GitLabUnitPrimitive

__all__ = [
    "Toolset",
    "BaseToolsRegistry",
]


class Toolset(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    required_unit_primitive: GitLabUnitPrimitive
    tools: list[BaseTool]

    # Minimum required GitLab version to use the tools.
    # If it's not set, the tools are available for all GitLab versions.
    min_required_gl_version: Optional[str] = None

    def is_available_for(self, user: GitLabUser, gl_version: str):
        if not user.can(self.name):
            return False

        if not self.min_required_gl_version:
            return True

        if not gl_version:
            return False

        try:
            return Version(self.min_required_gl_version) <= Version(gl_version)
        except InvalidVersion:
            return False


class BaseToolsRegistry(ABC):
    @abstractmethod
    def get_on_behalf(self, user: GitLabUser, gl_version: str) -> list[BaseTool]:
        pass

    @abstractmethod
    def get_all(self) -> list[BaseTool]:
        pass
