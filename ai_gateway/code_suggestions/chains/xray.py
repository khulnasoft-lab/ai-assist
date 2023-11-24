from typing import Optional, Any, Literal

from langchain.chat_models import ChatAnthropic
from langchain.output_parsers.json import SimpleJsonOutputParser
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable, RunnableLambda
from pydantic import BaseModel, Field, conlist, constr, Json

import structlog

log = structlog.stdlib.get_logger("codesuggestions")

__all__ = [
    "PROMPT_TEMPLATE",
    "PROMPT_TEMPLATE_CONTEXT",
    "QAChainDataInput",
    "ContextQAChainDataInput",
    "QAChainDataOutput",
    "qa_eval_chain",
    "qa_context_eval_chain",
]


PROMPT_TEMPLATE = """
{prompt_text}

{content}
""".strip(
    "\n"
)

class XRayChainFormatOutput(BaseModel):
    libraries: conlist(constr(min_length=1))

class XRayPackageFile(BaseModel):
    content: constr(max_length=100000)
    prompt_text: constr(max_length=100000)

class AnyPromptComponent(BaseModel):
    type: constr(strip_whitespace=True, max_length=255)
    payload: Json[Any]
    metadata: Optional[Json[Any]]

class XRayPackageFilePromptComponent(AnyPromptComponent):
    type: Literal["x_ray_package_file"] = "x_ray_package_file"
    payload: XRayPackageFile

class XRayRequest(BaseModel):
    prompt_components: conlist(XRayPackageFilePromptComponent)

def unpack_package_file(data: XRayRequest) -> dict[str, str]:
    return dict(data.prompt_components[0].payload)

def x_ray_chain() -> Runnable[dict, constr()]:
    model = ChatAnthropic(model="claude-2")
    model.temperature = 0
    prompt = PromptTemplate(
        input_variables=list(XRayPackageFile.__fields__.keys()),
        template=PROMPT_TEMPLATE,
        # partial_variables={"output_format": parser.get_format_instructions()},
    )

    chain = (
       RunnableLambda(unpack_package_file) | prompt | model | SimpleJsonOutputParser()
    )
    
    return chain
