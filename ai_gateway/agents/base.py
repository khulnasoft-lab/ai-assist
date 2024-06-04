from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Sequence, Tuple, Type, TypeVar

from jinja2 import BaseLoader, Environment
from langchain_core.messages import AIMessage
from langchain_core.prompts.chat import MessageLikeRepresentation
from langchain_core.runnables import Runnable, RunnableBinding
from pydantic import BaseModel

__all__ = ["Agent", "BaseAgentRegistry"]

Input = TypeVar("Input")
Output = TypeVar("Output")

jinja_env = Environment(loader=BaseLoader())


def _format_str(content: str, options: dict[str, Any]) -> str:
    return jinja_env.from_string(content).render(options)


def input_parser(input: BaseModel) -> dict:
    """Basic input parser that transforms a `BaseModel` to a `dict`. Agents may create
    their own input parsers to implement more complex logic.
    """
    return input.model_dump()


def output_parser(
    klass: Type[BaseModel], field: str
) -> Callable[[AIMessage], BaseModel]:
    """Basic output parser that transforms the LLM response into the specified model.
    It assumes the model has a single field. Agents may create their own output parsers
    to implement more complex logic.
    """

    def parser(message: AIMessage) -> BaseModel:
        return klass(**{field: message.content})

    return parser


class Agent(RunnableBinding[Input, Output]):
    def __init__(self, name: str, chain: Runnable):
        super().__init__(bound=chain)
        self.name = name

    # Assume that the prompt template keys map to roles. Subclasses can
    # override this method to implement more complex logic.
    @staticmethod
    def _prompt_template_to_messages(
        tpl: dict[str, str], options: dict[str, Any]
    ) -> list[Tuple[str, str]]:
        return list(tpl.items())

    @classmethod
    def build_messages(
        cls, prompt_template: dict[str, str], options: dict[str, Any]
    ) -> Sequence[MessageLikeRepresentation]:
        messages = []

        for role, template in cls._prompt_template_to_messages(
            prompt_template, options
        ):
            messages.append((role, _format_str(template, options)))

        return messages


class BaseAgentRegistry(ABC):
    @abstractmethod
    def get(
        self, use_case: str, agent_type: str, options: Optional[dict[str, Any]]
    ) -> Agent:
        pass
