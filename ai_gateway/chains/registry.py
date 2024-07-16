from pathlib import Path
from typing import Any, NamedTuple, Optional, Protocol, Type, cast

import yaml
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from ai_gateway.chains.base import BaseChainRegistry, Chain
from ai_gateway.chains.config import ChainConfig, ModelClassProvider, ModelConfig
from ai_gateway.chains.typing import ModelMetadata

__all__ = ["LocalChainRegistry", "ChainRegistered", "CustomModelsChainRegistry"]


class TypeModelFactory(Protocol):
    def __call__(self, *, model: str, **kwargs: Optional[Any]) -> BaseChatModel: ...


class ChainRegistered(NamedTuple):
    klass: Type[Chain]
    config: ChainConfig


class LocalChainRegistry(BaseChainRegistry):
    key_chain_type_base: str = "base"

    def __init__(
        self,
        chains_registered: dict[str, ChainRegistered],
        model_factories: dict[ModelClassProvider, TypeModelFactory],
    ):
        self.chains_registered = chains_registered
        self.model_factories = model_factories

    def _resolve_id(self, chain_id: str) -> str:
        _, _, chain_type = chain_id.partition("/")
        if chain_type:
            # the `chain_id` value is already in the format of - `first/last`
            return chain_id

        return f"{chain_id}/{self.key_chain_type_base}"

    def _get_model(
        self,
        config_model: ModelConfig,
        model_metadata: Optional[ModelMetadata] = None,
    ) -> BaseChatModel:
        model_class_provider = config_model.params.model_class_provider
        if model_factory := self.model_factories.get(model_class_provider, None):
            return model_factory(
                model=config_model.name,
                **config_model.params.model_dump(
                    exclude={"model_class_provider"}, exclude_none=True, by_alias=True
                ),
            )

        raise ValueError(f"unrecognized model class provider `{model_class_provider}`.")

    def get(
        self,
        chain_id: str,
        options: Optional[dict[str, Any]] = None,
        model_metadata: Optional[ModelMetadata] = None,
    ) -> Chain:
        chain_id = self._resolve_id(chain_id)
        klass, config = self.chains_registered[chain_id]

        model = self._get_model(config.model, model_metadata)

        if config.stop:
            model = cast(BaseChatModel, model.bind(stop=config.stop))

        messages = klass.build_messages(config.prompt_template, options or {})
        prompt = ChatPromptTemplate.from_messages(messages)

        return klass(
            name=config.name,
            chain=prompt | model,
            unit_primitives=config.unit_primitives,
        )

    @classmethod
    def from_local_yaml(
        cls,
        class_overrides: dict[str, Type[Chain]],
        model_factories: dict[ModelClassProvider, TypeModelFactory],
    ) -> "LocalChainRegistry":
        """Iterate over all chain definition files matching [usecase]/[type].yml,
        and create a corresponding chain for each one. The base Chain class is
        used if no matching override is provided in `class_overrides`.
        """

        chains_definitions_dir = Path(__file__).parent / "definitions"
        chains_registered = {}
        for path in chains_definitions_dir.glob("*/*.yml"):
            chain_id = str(
                # E.g., "chat/react", "generate_description/base", etc.
                path.relative_to(chains_definitions_dir).with_suffix("")
            )

            with open(path, "r") as fp:
                klass = class_overrides.get(chain_id, Chain)
                chains_registered[chain_id] = ChainRegistered(
                    klass=klass, config=ChainConfig(**yaml.safe_load(fp))
                )

        return cls(chains_registered, model_factories)


class CustomModelsChainRegistry(LocalChainRegistry):
    def _get_model(
        self,
        config_model: ModelConfig,
        model_metadata: Optional[ModelMetadata] = None,
    ) -> BaseChatModel:
        chat_model = super()._get_model(config_model)

        if model_metadata is None:
            return chat_model

        return cast(
            BaseChatModel,
            chat_model.bind(
                model=model_metadata.name,
                api_base=str(model_metadata.endpoint),
                custom_llm_provider=model_metadata.provider,
                api_key=model_metadata.api_key,
            ),
        )

    def get(
        self,
        chain_id: str,
        options: Optional[dict[str, Any]] = None,
        model_metadata: Optional[ModelMetadata] = None,
    ) -> Chain:
        if model_metadata is not None:
            chain_id = f"{chain_id}-custom"

        return super().get(chain_id, options, model_metadata)
