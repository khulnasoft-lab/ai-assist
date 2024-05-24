from typing import Any, Dict

from jinja2 import BaseLoader, Environment
from langchain_core.language_models.chat_models import BaseChatModel

__all__ = ["Agent"]


class Agent:
    def __init__(
        self, name: str, model: BaseChatModel, prompt_templates: Dict[str, str]
    ):
        self.name = name
        self.model = model
        self.prompt_templates = prompt_templates
        self.jinja_env = Environment(loader=BaseLoader())

    def prompt(self, key: str, **kwargs: Any):
        try:
            return self.jinja_env.from_string(self.prompt_templates[key]).render(
                **kwargs
            )
        except KeyError:
            return None
