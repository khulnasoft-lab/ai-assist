import pytest

from ai_gateway.agents.base import Agent
from ai_gateway.chat.agents.utils import convert_prompt_to_messages
from ai_gateway.models import Message, Role


@pytest.mark.parametrize(
    ("agent", "prompt_kwargs", "expected"),
    [
        (
            Agent(name="Test", model=None, prompt_templates={"user": "user prompt"}),
            {},
            [(Role.USER, "user prompt")],
        ),
        (
            Agent(
                name="Test",
                model=None,
                prompt_templates={"user": "user prompt {{text}}"},
            ),
            {"text": "!"},
            [(Role.USER, "user prompt !")],
        ),
        (
            Agent(
                name="Test",
                model=None,
                prompt_templates={"system": "system prompt", "user": "user prompt"},
            ),
            {},
            [
                (Role.SYSTEM, "system prompt"),
                (Role.USER, "user prompt"),
            ],
        ),
        (
            Agent(
                name="Test",
                model=None,
                prompt_templates={
                    "system": "system prompt",
                    "user": "user prompt",
                    "assistant": "assistant prompt",
                },
            ),
            {},
            [
                (Role.SYSTEM, "system prompt"),
                (Role.USER, "user prompt"),
                (Role.ASSISTANT, "assistant prompt"),
            ],
        ),
        (
            Agent(
                name="Test",
                model=None,
                prompt_templates={
                    "system": "system prompt",
                    "user": "user prompt {{text}}",
                    "assistant": "assistant prompt",
                },
            ),
            {"text": "!"},
            [
                (Role.SYSTEM, "system prompt"),
                (Role.USER, "user prompt !"),
                (Role.ASSISTANT, "assistant prompt"),
            ],
        ),
        (
            Agent(
                name="Test",
                model=None,
                prompt_templates={
                    "system": "system prompt {{text}}",
                    "user": "user prompt {{text}}",
                    "assistant": "assistant prompt {{text}}",
                },
            ),
            {"text": "!"},
            [
                (Role.SYSTEM, "system prompt !"),
                (Role.USER, "user prompt !"),
                (Role.ASSISTANT, "assistant prompt !"),
            ],
        ),
    ],
)
def test_convert_prompt_to_messages(
    agent: Agent, prompt_kwargs: dict, expected: list[Message]
):
    actual = convert_prompt_to_messages(agent, **prompt_kwargs)
    assert actual == expected
