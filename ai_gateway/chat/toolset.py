from ai_gateway.auth import GitLabUser
from ai_gateway.chat.base import BaseToolsRegistry, Toolset
from ai_gateway.chat.tools import BaseTool
from ai_gateway.chat.tools.gitlab import (
    CiEditorAssistant,
    EpicReader,
    GitlabDocumentation,
    IssueReader,
)
from ai_gateway.gitlab_features import GitLabUnitPrimitive

__all__ = ["DuoChatToolsRegistry"]


class DuoChatToolsRegistry(BaseToolsRegistry):
    @property
    def toolsets(self) -> list[Toolset]:
        # We can also read the list of tools and associated unit primitives from the file
        # similar to what we implemented for the Prompt Registry
        return [
            Toolset(
                required_unit_primitive=GitLabUnitPrimitive.DUO_CHAT,
                min_required_gl_version=None,
                tools=[
                    CiEditorAssistant(),
                    IssueReader(),
                    EpicReader(),
                ],
            ),
            Toolset(
                required_unit_primitive=GitLabUnitPrimitive.DOCUMENTATION_SEARCH,
                min_required_gl_version=None,
                tools=[GitlabDocumentation()],
            ),
        ]

    def get_on_behalf(self, user: GitLabUser, gl_version: str) -> list[BaseTool]:
        tools = []

        for toolset in self.toolsets:
            if toolset.is_available_for(user, gl_version):
                tools.extend(toolset.tools)

        return tools

    def get_all(self) -> list[BaseTool]:
        tools = []
        for toolset in self.toolsets:
            tools.extend(toolset.tools)

        return tools
