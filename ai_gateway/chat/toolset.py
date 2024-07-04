from gitlab_cloud_connector import UnitPrimitive, WrongUnitPrimitives

from ai_gateway.auth import GitLabUser
from ai_gateway.chat.base import BaseToolsRegistry, UnitPrimitiveToolset
from ai_gateway.chat.tools import BaseTool
from ai_gateway.chat.tools.gitlab import (
    CiEditorAssistant,
    EpicReader,
    GitlabDocumentation,
    IssueReader,
)

__all__ = ["DuoChatToolsRegistry"]


class DuoChatToolsRegistry(BaseToolsRegistry):
    @property
    def toolsets(self) -> list[UnitPrimitiveToolset]:
        # We can also read the list of tools and associated unit primitives from the file
        # similar to what we implemented for the Agent Registry
        return [
            UnitPrimitiveToolset(
                name=UnitPrimitive.DUO_CHAT,
                min_required_gl_version=None,
                tools=[
                    CiEditorAssistant(),
                    IssueReader(),
                    EpicReader(),
                ],
            ),
            UnitPrimitiveToolset(
                name=UnitPrimitive.DOCUMENTATION_SEARCH,
                min_required_gl_version=None,
                tools=[GitlabDocumentation()],
            ),
        ]

    def get_on_behalf(
        self, user: GitLabUser, raise_exception: bool = True
    ) -> list[BaseTool]:
        tools = []
        user_unit_primitives = user.unit_primitives

        for toolset in self.toolsets:
            if toolset.name in user_unit_primitives:
                # Consider tool versioning - https://gitlab.com/gitlab-org/gitlab/-/issues/466247
                tools.extend(toolset.tools)

        if len(tools) == 0 and raise_exception:
            raise WrongUnitPrimitives(
                "user doesn't have access to any of the unit primitives"
            )

        return tools

    def get_all(self) -> list[BaseTool]:
        tools = []
        for toolset in self.toolsets:
            tools.extend(toolset.tools)

        return tools
