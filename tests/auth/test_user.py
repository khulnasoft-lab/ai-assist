import pytest
from gitlab_cloud_connector import UnitPrimitive

from ai_gateway.auth.user import GitLabUser, UserClaims


@pytest.fixture
def user():
    return GitLabUser(
        authenticated=True,
        claims=UserClaims(
            scopes=["code_suggestions"],
            subject="1234",
            gitlab_realm="self-managed",
            issuer="https://customers.gitlab.com",
        ),
    )


def test_issuer_not_in_disallowed_issuers(user: GitLabUser):
    assert user.can(
        UnitPrimitive.CODE_SUGGESTIONS, disallowed_issuers=["gitlab-ai-gateway"]
    )


def test_issuer_in_disallowed_issuers(user: GitLabUser):
    assert not user.can(
        UnitPrimitive.CODE_SUGGESTIONS,
        disallowed_issuers=["https://customers.gitlab.com"],
    )


@pytest.mark.parametrize(
    ("user", "expected_unit_primitives"),
    [
        (
            GitLabUser(
                authenticated=True, claims=UserClaims(scopes=["code_suggestions"])
            ),
            [UnitPrimitive.CODE_SUGGESTIONS],
        ),
        (
            GitLabUser(
                authenticated=True,
                claims=UserClaims(scopes=["code_suggestions", "unknown"]),
            ),
            [UnitPrimitive.CODE_SUGGESTIONS],
        ),
        (GitLabUser(authenticated=True, claims=None), []),
    ],
)
def test_user_unit_primitives(
    user: GitLabUser,
    expected_unit_primitives: list[UnitPrimitive],
):
    actual_unit_primitives = user.unit_primitives

    assert actual_unit_primitives == expected_unit_primitives
