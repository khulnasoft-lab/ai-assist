from typing import Generic, TypeVar

from pydantic import BaseModel

from ai_gateway.chains.config.models import TypeModelParams
from ai_gateway.gitlab_features import GitLabUnitPrimitive

__all__ = ["BaseChainConfig", "ChainConfig", "ModelConfig"]


# Chains may operate with unit primitives in various ways.
# Basic agents typically use plain strings as unit primitives.
# More sophisticated agents, like Duo Chat, assign unit primitives to specific tools.
# Creating a generic UnitPrimitiveType enables storage of unit primitives in any desired format.
TypeUnitPrimitive = TypeVar("TypeUnitPrimitive")


class ModelConfig(BaseModel):
    name: str
    params: TypeModelParams


class BaseChainConfig(BaseModel, Generic[TypeUnitPrimitive]):
    name: str
    model: ModelConfig
    unit_primitives: list[TypeUnitPrimitive]
    prompt_template: dict[str, str]
    stop: list[str] | None = None


class ChainConfig(BaseChainConfig):
    unit_primitives: list[GitLabUnitPrimitive]
