from typing import Any, Optional, Tuple

from langchain_core.runnables import Runnable
from pydantic import BaseModel

from ai_gateway.agents.base import Agent, input_parser, output_parser


class GenerateDescriptionInputs(BaseModel):
    content: str
    template: Optional[str]


class GenerateDescriptionOutput(BaseModel):
    description: str


class GenerateDescriptionAgent(
    Agent[GenerateDescriptionInputs, GenerateDescriptionOutput]
):
    def __init__(self, name: str, chain: Runnable):
        chain = (
            input_parser
            | chain
            | output_parser(GenerateDescriptionOutput, "description")
        )
        super().__init__(name, chain)

    @staticmethod
    def _prompt_template_to_messages(
        tpl: dict[str, str], options: dict[str, Any]
    ) -> list[Tuple[str, str]]:
        prompt_template = "with_template" if options["template"] else "without_template"

        return [("user", tpl[prompt_template])]
