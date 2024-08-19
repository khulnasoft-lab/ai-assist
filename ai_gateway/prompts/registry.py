import random
from pathlib import Path
from typing import Any, NamedTuple, Optional, Type

import yaml

from ai_gateway.prompts.base import BasePromptRegistry, Prompt
from ai_gateway.prompts.config import ModelClassProvider, PromptConfig
from ai_gateway.prompts.typing import ModelMetadata, TypeModelFactory

__all__ = ["LocalPromptRegistry", "PromptRegistered"]


class PromptRegistered(NamedTuple):
    klass: Type[Prompt]
    config: PromptConfig


class LocalPromptRegistry(BasePromptRegistry):
    key_prompt_type_base: str = "base"

    def __init__(
        self,
        prompts_registered: dict[str, PromptRegistered],
        model_factories: dict[ModelClassProvider, TypeModelFactory],
        routers: dict[str, Any],
        custom_models_enabled: bool,
    ):
        self.prompts_registered = prompts_registered
        self.model_factories = model_factories
        self.routers = routers
        self.custom_models_enabled = custom_models_enabled

    def _resolve_id(
        self,
        prompt_id: str,
        model_metadata: Optional[ModelMetadata] = None,
    ) -> str:
        if model_metadata:
            return f"{prompt_id}/{model_metadata.name}"

        return f"{prompt_id}/{self.key_prompt_type_base}"

    def get(
        self,
        prompt_id: str,
        options: Optional[dict[str, Any]] = None,
        model_metadata: Optional[ModelMetadata] = None,
    ) -> Prompt:
        if (
            model_metadata
            and model_metadata.endpoint
            and not self.custom_models_enabled
        ):
            raise ValueError(
                "Endpoint override not allowed when custom models are disabled."
            )

        prompt_id = self._resolve_id(prompt_id, model_metadata)

        klass, config = self.prompts_registered[prompt_id]

        model_factory, model_name = self._get_model_info()

        print("----------------")
        print(model_factory)
        print(model_name)
        print("----------------")

        config.name = model_name

        return klass(model_factory, config, model_metadata, options)

    def _get_model_info(self):
        router = self.routers["default"]
        model_config = self._select_model(router)
        model_factory = self.model_factories.get(model_config["provider"], None)

        return model_factory, model_config["model"]

    def _select_model(self, router):
        rand = random.randint(1, 100)

        cumulative_percentage = 0
        for model in router["models"]:
            cumulative_percentage += model["router_params"]["percentage"]
            if rand <= cumulative_percentage:
                return model

    @classmethod
    def from_local_yaml(
        cls,
        class_overrides: dict[str, Type[Prompt]],
        model_factories: dict[ModelClassProvider, TypeModelFactory],
        routers: dict[str, Any],
        custom_models_enabled: bool = False,
    ) -> "LocalPromptRegistry":
        """Iterate over all prompt definition files matching [usecase]/[type].yml,
        and create a corresponding prompt for each one. The base Prompt class is
        used if no matching override is provided in `class_overrides`.
        """

        prompts_definitions_dir = Path(__file__).parent / "definitions"
        prompts_registered = {}

        for path in prompts_definitions_dir.glob("**/*.yml"):
            prompt_id_with_model_name = str(
                # E.g., "chat/react/base", "generate_description/mistral", etc.
                path.relative_to(prompts_definitions_dir).with_suffix("")
            )

            # Remove model name, for example: to receive "chat/react" from "chat/react/mistral"
            prompt_id, _, _ = prompt_id_with_model_name.rpartition("/")

            with open(path, "r") as fp:
                klass = class_overrides.get(prompt_id, Prompt)
                prompts_registered[prompt_id_with_model_name] = PromptRegistered(
                    klass=klass, config=PromptConfig(**yaml.safe_load(fp))
                )

        return cls(prompts_registered, model_factories, routers, custom_models_enabled)
