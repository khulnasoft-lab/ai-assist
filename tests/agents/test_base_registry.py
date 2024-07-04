import pytest
from gitlab_cloud_connector import UnitPrimitive, WrongUnitPrimitives
from langchain_core.runnables import chain

from ai_gateway.agents import Agent, BaseAgentRegistry
from ai_gateway.auth.user import GitLabUser, UserClaims


@pytest.fixture
def user(scopes: list[str]):
    yield GitLabUser(authenticated=True, claims=UserClaims(scopes=scopes))


@pytest.fixture
def agent(unit_primitives: list[UnitPrimitive]):
    @chain
    def runnable(*args, **kwargs): ...

    yield Agent(name="test", unit_primitives=unit_primitives, chain=runnable)


@pytest.fixture
def registry(agent: Agent):
    class Registry(BaseAgentRegistry):
        def get(self, *args, **kwargs):
            return agent

    yield Registry()


class TestBaseRegistry:
    @pytest.mark.parametrize(
        ("unit_primitives", "scopes", "success"),
        [
            ([UnitPrimitive.CODE_SUGGESTIONS], ["code_suggestions"], True),
            (
                [
                    UnitPrimitive.CODE_SUGGESTIONS,
                    UnitPrimitive.ANALYZE_CI_JOB_FAILURE,
                ],
                ["code_suggestions", "analyze_ci_job_failure"],
                True,
            ),
            ([UnitPrimitive.CODE_SUGGESTIONS], [], False),
            (
                [
                    UnitPrimitive.CODE_SUGGESTIONS,
                    UnitPrimitive.ANALYZE_CI_JOB_FAILURE,
                ],
                ["code_suggestions"],
                False,
            ),
        ],
    )
    def test_get_on_behalf(
        self,
        registry: BaseAgentRegistry,
        user: GitLabUser,
        agent: Agent,
        unit_primitives: list[UnitPrimitive],
        scopes: list[str],
        success: bool,
    ):
        if success:
            assert registry.get_on_behalf(user=user, agent_id="test") == agent
        else:
            with pytest.raises(WrongUnitPrimitives):
                registry.get_on_behalf(user=user, agent_id="test")
