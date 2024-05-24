from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

import yaml
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel

from ai_gateway.agents.base import Agent

__all__ = ["BaseAgentRegistry", "LocalAgentRegistry"]


class BaseAgentRegistry(ABC):
    @abstractmethod
    def get(self, usecase: str, key: str) -> Agent:
        pass


class LocalAgentRegistry(BaseAgentRegistry):
    # TODO: Generalize to models from any provider
    def __init__(self):
        self.base_path = Path(__file__).parent

    @lru_cache
    def get(self, usecase: str, key: str) -> Agent:
        with open(self.base_path / usecase / f"{key}.yml", "r") as f:
            agent_definition = yaml.safe_load(f)

        model = self._model(
            provider=agent_definition["provider"],
            name=agent_definition["model"],
        )

        return Agent(
            name=agent_definition["name"],
            model=model,
            prompt_templates=agent_definition["prompt_templates"],
        )

    def _model(self, provider: str, name: str) -> BaseChatModel:
        match provider:
            case "anthropic":
                return ChatAnthropic(model=name)
            case _:
                raise ValueError(f"Unknown provider: {provider}")
