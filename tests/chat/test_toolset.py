from typing import Type

import pytest

from ai_gateway.auth import GitLabUser, UserClaims
from ai_gateway.chat.tools import BaseTool
from ai_gateway.chat.tools.gitlab import (
    CiEditorAssistant,
    EpicReader,
    GitlabDocumentation,
    IssueReader,
)
from ai_gateway.chat.toolset import DuoChatToolsRegistry
from ai_gateway.gitlab_features import WrongUnitPrimitives
from ai_gateway.cloud_connector.unit_primitive import GitLabUnitPrimitive


class TestDuoChatToolRegistry:
    @pytest.mark.parametrize(
        "expected_tools",
        [
            (
                [
                    CiEditorAssistant,
                    IssueReader,
                    EpicReader,
                    GitlabDocumentation,
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
            (
                [GitLabUnitPrimitive.DUO_CHAT],
                [CiEditorAssistant, IssueReader, EpicReader],
            ),
            ([GitLabUnitPrimitive.DOCUMENTATION_SEARCH], [GitlabDocumentation]),
            (
                [
                    GitLabUnitPrimitive.DUO_CHAT,
                    GitLabUnitPrimitive.DOCUMENTATION_SEARCH,
                ],
                [CiEditorAssistant, IssueReader, EpicReader, GitlabDocumentation],
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

        tools = DuoChatToolsRegistry().get_on_behalf(user, raise_exception=False)
        actual_tools = [type(tool) for tool in tools]

        assert actual_tools == expected_tools

    @pytest.mark.parametrize(
        "unit_primitives",
        [([GitLabUnitPrimitive.CODE_SUGGESTIONS, GitLabUnitPrimitive.EXPLAIN_CODE])],
    )
    def test_get_on_behalf_error(
        self,
        unit_primitives: list[GitLabUnitPrimitive],
    ):
        user = GitLabUser(
            authenticated=True,
            claims=UserClaims(scopes=[u.value for u in unit_primitives]),
        )

        with pytest.raises(WrongUnitPrimitives):
            DuoChatToolsRegistry().get_on_behalf(user, raise_exception=True)
