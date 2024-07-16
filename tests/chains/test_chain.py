import pytest
from langchain_core import runnables
from pydantic.v1.error_wrappers import ValidationError

from ai_gateway.chains.base import Chain
from ai_gateway.gitlab_features import GitLabUnitPrimitive


@pytest.fixture
def prompt_template() -> dict[str, str]:
    return {"system": "Hi, I'm {{name}}", "user": "{{content}}"}


class TestChain:
    def test_initialize(self):
        @runnables.chain
        def runnable(): ...

        chain = Chain(
            name="test", chain=runnable, unit_primitives=["analyze_ci_job_failure"]
        )

        assert chain.name == "test"
        assert chain.bound == runnable  # pylint: disable=comparison-with-callable
        assert chain.unit_primitives == [GitLabUnitPrimitive.ANALYZE_CI_JOB_FAILURE]

    def test_invalid_initialize(self):
        @runnables.chain
        def runnable(): ...

        with pytest.raises(ValidationError):
            Chain(name="test", chain=runnable, unit_primitives=["invalid"])

    def test_build_messages(self, prompt_template):
        messages = Chain.build_messages(
            prompt_template, {"name": "Duo", "content": "What's up?"}
        )

        assert messages == [("system", "Hi, I'm Duo"), ("user", "What's up?")]
