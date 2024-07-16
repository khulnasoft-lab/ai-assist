import pytest
from langchain_core import runnables

from ai_gateway.auth.user import GitLabUser, UserClaims
from ai_gateway.chains import BaseChainRegistry, Chain
from ai_gateway.gitlab_features import GitLabUnitPrimitive, WrongUnitPrimitives


@pytest.fixture
def user(scopes: list[str]):
    yield GitLabUser(authenticated=True, claims=UserClaims(scopes=scopes))


@pytest.fixture
def chain(unit_primitives: list[GitLabUnitPrimitive]):
    @runnables.chain
    def runnable(*args, **kwargs): ...

    yield Chain(name="test", unit_primitives=unit_primitives, chain=runnable)


@pytest.fixture
def registry(chain: Chain):
    class Registry(BaseChainRegistry):
        def get(self, *args, **kwargs):
            return chain

    yield Registry()


class TestBaseRegistry:
    @pytest.mark.parametrize(
        ("unit_primitives", "scopes", "success"),
        [
            ([GitLabUnitPrimitive.CODE_SUGGESTIONS], ["code_suggestions"], True),
            (
                [
                    GitLabUnitPrimitive.CODE_SUGGESTIONS,
                    GitLabUnitPrimitive.ANALYZE_CI_JOB_FAILURE,
                ],
                ["code_suggestions", "analyze_ci_job_failure"],
                True,
            ),
            ([GitLabUnitPrimitive.CODE_SUGGESTIONS], [], False),
            (
                [
                    GitLabUnitPrimitive.CODE_SUGGESTIONS,
                    GitLabUnitPrimitive.ANALYZE_CI_JOB_FAILURE,
                ],
                ["code_suggestions"],
                False,
            ),
        ],
    )
    def test_get_on_behalf(
        self,
        registry: BaseChainRegistry,
        user: GitLabUser,
        chain: Chain,
        unit_primitives: list[GitLabUnitPrimitive],
        scopes: list[str],
        success: bool,
    ):
        if success:
            assert registry.get_on_behalf(user=user, chain_id="test") == chain
        else:
            with pytest.raises(WrongUnitPrimitives):
                registry.get_on_behalf(user=user, chain_id="test")
