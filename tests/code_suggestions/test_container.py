import pytest
from dependency_injector import containers

from ai_gateway.code_suggestions.completions import (
    CodeCompletions,
    CodeCompletionsLegacy,
)
from ai_gateway.code_suggestions.generations import CodeGenerations
from ai_gateway.models.anthropic import KindAnthropicModel
from ai_gateway.models.litellm import KindLiteLlmModel


@pytest.mark.asyncio
async def test_container(mock_container: containers.DeclarativeContainer):
    code_suggestions = mock_container.code_suggestions
    completions = code_suggestions.completions
    generations = code_suggestions.generations

    assert isinstance(await completions.vertex_legacy(), CodeCompletionsLegacy)
    assert isinstance(await completions.anthropic(), CodeCompletions)
    assert isinstance(
        completions.litellm_factory(model__name=KindLiteLlmModel.MISTRAL),
        CodeCompletions,
    )
    assert isinstance(await generations.vertex(), CodeGenerations)
    assert isinstance(
        await generations.anthropic_factory(
            model__name=KindAnthropicModel.CLAUDE_3_HAIKU
        ),
        CodeGenerations,
    )
    assert isinstance(
        await generations.anthropic_chat_factory(
            model__name=KindAnthropicModel.CLAUDE_3_HAIKU
        ),
        CodeGenerations,
    )
    assert isinstance(
        generations.litellm_factory(model__name=KindLiteLlmModel.MISTRAL),
        CodeGenerations,
    )
    assert isinstance(await generations.anthropic_default(), CodeGenerations)
