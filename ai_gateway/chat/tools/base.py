from abc import ABC
from typing import Any, Optional

from gitlab_cloud_connector import GitLabUnitPrimitive
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel

__all__ = [
    "BaseTool",
    "BaseRemoteTool",
]


class BaseTool(ABC, BaseModel, frozen=True):
    name: str
    description: str
    unit_primitive: GitLabUnitPrimitive
    min_required_gl_version: Optional[str] = None
    resource: Optional[str] = None
    example: Optional[str] = None

    def is_compatible(self, gl_version: str) -> bool:
        if not self.min_required_gl_version:
            return True

        if not gl_version:
            return False

        try:
            return Version(self.min_required_gl_version) <= Version(gl_version)
        except InvalidVersion:
            return False

    def get_tool_config(self) -> dict:
        return {
            "name": self.name,
            "description": f"{self.description}\n\nExample:\n{self.example}",
            "input_schema": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                    },
                    "action": {
                        "type": "string",
                        "description": f"Should always be {self.name}",
                    },
                    "action_input": {
                        "type": "string",
                        "description": "The original question/request",
                    },
                },
                "required": ["thought", "action", "action_input"],
            },
        }


class BaseRemoteTool(BaseTool):
    def _run(self, *args: Any, **kwargs: Any) -> Any:
        # By default, we run tools on the Ruby app side
        raise NotImplementedError(
            "Please check the Rails app for an implementation of this tool."
        )
