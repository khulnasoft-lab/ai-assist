from enum import Enum
from pathlib import Path
from typing import Any, Optional, Protocol, Type

import yaml
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from ai_gateway.agents.base import Agent, BaseAgentRegistry

__all__ = ["LocalAgentRegistry", "ModelProvider"]


class ModelProvider(str, Enum):
    ANTHROPIC = "anthropic"


class ModelFactoryType(Protocol):
    def __call__(
        self, *, model: str, **model_kwargs: Optional[Any]
    ) -> BaseChatModel: ...


class LocalAgentRegistry(BaseAgentRegistry):
    def __init__(
        self,
        agent_definitions: dict[str, tuple[Type[Agent], dict]],
        model_factories: dict[ModelProvider, ModelFactoryType],
    ):
        self.agent_definitions = agent_definitions
        self.model_factories = model_factories

    def _get_model(
        self, provider: str, name: str, **kwargs: Optional[Any]
    ) -> BaseChatModel:
        if model_factory := self.model_factories.get(ModelProvider(provider), None):
            return model_factory(model=name, **kwargs)

        raise ValueError(f"unknown provider `{provider}`.")

    def get(self, id: str, options: Optional[dict[str, Any]] = None) -> Any:
        klass, config = self.agent_definitions[id]

        # TODO: read model parameters such as `temperature`, `top_k`
        #  and pass them to the model factory via **kwargs.
        model: Runnable = self._get_model(
            provider=config["provider"],
            name=config["model"],
        )

        if "stop" in config:
            model = model.bind(stop=config["stop"])

        messages = klass.build_messages(config["prompt_template"], options or {})
        prompt = ChatPromptTemplate.from_messages(messages)

        return klass(
            name=config["name"],
            chain=prompt | model,
            unit_primitives=config["unit_primitives"],
        )

    @classmethod
    def from_local_yaml(
        cls,
        model_factories: dict[ModelProvider, ModelFactoryType],
        class_overrides: dict[str, Type[Agent]],
    ) -> "LocalAgentRegistry":
        """Iterate over all agent definition files matching [usecase]/[type].yml,
        and create a corresponding agent for each one. The base Agent class is
        used if no matching override is provided in `class_overrides`.
        """

        agent_definitions = {}
        for path in Path(__file__).parent.glob("*/*.yml"):
            with open(path, "r") as fp:
                klass = class_overrides.get(path.stem, Agent)
                agent_definitions[path.stem] = (klass, yaml.safe_load(fp))

        return cls(agent_definitions, model_factories)
