from typing import Any

from langchain_core.prompts.chat import MessageLikeRepresentation

from ai_gateway.agents.base import Agent
from ai_gateway.models import Role

__all__ = [
    "convert_prompt_to_messages",
]


def convert_prompt_to_messages(
    agent: Agent, **kwargs: Any
) -> list[MessageLikeRepresentation]:
    messages = []
    for role in Role:
        content = agent.prompt(role, **kwargs)
        if content is None:
            continue

        messages.append((role, content))

    return messages
