from ai_gateway.auth import GitLabUser
from ai_gateway.chat.base import BaseToolsRegistry
from ai_gateway.chat.tools import BaseTool
from ai_gateway.chat.tools.gitlab import (
    BuildReader,
    CiEditorAssistant,
    CommitReader,
    EpicReader,
    GitlabDocumentation,
    IssueReader,
    MergeRequestReader,
)
from ai_gateway.feature_flags import FeatureFlag, is_feature_enabled

__all__ = ["DuoChatToolsRegistry"]


class DuoChatToolsRegistry(BaseToolsRegistry):
    @property
    def tools(self) -> list[BaseTool]:
        # We can also read the list of tools and associated unit primitives from the file
        # similar to what we implemented for the Prompt Registry
        tools = [
            CiEditorAssistant(),
            GitlabDocumentation(),
            EpicReader(),
            IssueReader(),
            MergeRequestReader(),
        ]

        if is_feature_enabled(FeatureFlag.AI_COMMIT_READER_FOR_CHAT):
            tools.append(CommitReader())

        if is_feature_enabled(FeatureFlag.AI_BUILD_READER_FOR_CHAT):
            tools.append(BuildReader())

        return tools

    def get_on_behalf(self, user: GitLabUser, gl_version: str) -> list[BaseTool]:
        _tools = []

        for tool in self.tools:
            if not user.can(tool.unit_primitive):
                continue

            if not tool.is_compatible(gl_version):
                continue

            _tools.append(tool)

        return _tools

    def get_all(self) -> list[BaseTool]:
        return self.tools
