from typing import Type

import pytest

from ai_gateway.auth import GitLabUser, UserClaims
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
from ai_gateway.chat.toolset import DuoChatToolsRegistry
from ai_gateway.feature_flags.context import current_feature_flag_context
from ai_gateway.gitlab_features import GitLabUnitPrimitive


class TestDuoChatToolRegistry:
    @pytest.mark.parametrize(
        "expected_tools",
        [
            (
                [
                    CiEditorAssistant,
                    GitlabDocumentation,
                    EpicReader,
                    IssueReader,
                    MergeRequestReader,
                ]
            )
        ],
    )
    def test_get_all_success(self, expected_tools: list[Type[BaseTool]]):
        tools = DuoChatToolsRegistry().get_all()
        actual_tools = [type(tool) for tool in tools]

        assert actual_tools == expected_tools

    @pytest.mark.parametrize(
        ("unit_primitives", "expected_tools"),
        [
            ([GitLabUnitPrimitive.DUO_CHAT], [CiEditorAssistant]),
            ([GitLabUnitPrimitive.DOCUMENTATION_SEARCH], [GitlabDocumentation]),
            ([GitLabUnitPrimitive.ASK_EPIC], [EpicReader]),
            ([GitLabUnitPrimitive.ASK_ISSUE], [IssueReader]),
            (
                [
                    GitLabUnitPrimitive.DUO_CHAT,
                    GitLabUnitPrimitive.DOCUMENTATION_SEARCH,
                    GitLabUnitPrimitive.ASK_EPIC,
                    GitLabUnitPrimitive.ASK_ISSUE,
                ],
                [
                    CiEditorAssistant,
                    GitlabDocumentation,
                    EpicReader,
                    IssueReader,
                ],
            ),
            (
                [GitLabUnitPrimitive.CODE_SUGGESTIONS],
                [],
            ),
        ],
    )
    def test_get_on_behalf_success(
        self,
        unit_primitives: list[GitLabUnitPrimitive],
        expected_tools: list[Type[BaseTool]],
    ):
        user = GitLabUser(
            authenticated=True,
            claims=UserClaims(scopes=[u.value for u in unit_primitives]),
        )

        tools = DuoChatToolsRegistry().get_on_behalf(user, "")
        actual_tools = [type(tool) for tool in tools]

        assert actual_tools == expected_tools

    @pytest.mark.parametrize(
        "unit_primitives",
        [([GitLabUnitPrimitive.CODE_SUGGESTIONS, GitLabUnitPrimitive.EXPLAIN_CODE])],
    )
    def test_get_on_behalf_empty(
        self,
        unit_primitives: list[GitLabUnitPrimitive],
    ):
        user = GitLabUser(
            authenticated=True,
            claims=UserClaims(scopes=[u.value for u in unit_primitives]),
        )

        tools = DuoChatToolsRegistry().get_on_behalf(user, "")

        assert len(tools) == 0

    @pytest.mark.parametrize(
        "feature_flag, unit_primitive, reader_tool_type",
        [
            ("ai_commit_reader_for_chat", GitLabUnitPrimitive.ASK_COMMIT, CommitReader),
            ("ai_build_reader_for_chat", GitLabUnitPrimitive.ASK_BUILD, BuildReader),
        ],
    )
    def test_feature_flag(
        self,
        feature_flag: str,
        unit_primitive: GitLabUnitPrimitive,
        reader_tool_type: Type[BaseTool],
    ):
        current_feature_flag_context.set({feature_flag})

        user = GitLabUser(
            authenticated=True,
            claims=UserClaims(
                scopes=[
                    unit_primitive.value,
                    GitLabUnitPrimitive.DUO_CHAT.value,
                ]
            ),
        )

        tools = DuoChatToolsRegistry().get_on_behalf(user, "17.5.0-pre")
        actual_tools = [type(tool) for tool in tools]

        assert actual_tools == [CiEditorAssistant, reader_tool_type]

        current_feature_flag_context.set(set())

        tools = DuoChatToolsRegistry().get_on_behalf(user, "17.5.0-pre")
        actual_tools = [type(tool) for tool in tools]

        assert actual_tools == [CiEditorAssistant]
