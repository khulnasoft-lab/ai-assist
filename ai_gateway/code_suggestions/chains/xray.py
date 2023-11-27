from typing import Optional, Any, Literal

from langchain.prompts import PromptTemplate
from pydantic import BaseModel, conlist, constr, Json, Field
from langchain.llms.anthropic import Anthropic
from langchain.schema.runnable import RunnableLambda, Runnable
from langchain.schema import StrOutputParser

import structlog

log = structlog.stdlib.get_logger("codesuggestions")

__all__ = [
    "PROMPT_TEMPLATE",
    "chain",
    "XRayRequest"
]

class PackageFilePromptPayload(BaseModel):
    template: constr(max_length=100000)
    variables: dict[str, str]

class AnyPromptComponent(BaseModel):
    type: constr(strip_whitespace=True, max_length=255)
    payload: Json
    metadata: Optional[Json]

class PackageFilePromptComponent(AnyPromptComponent):
    type: Literal["x_ray_package_file_prompt"] = "x_ray_package_file_prompt"
    payload: PackageFilePromptPayload

class XRayRequest(BaseModel):
    prompt_components: conlist(PackageFilePromptComponent)

def unpack_package_file_prompt(data: XRayRequest) -> dict[str, str]:    
    component = next(c for c in data.prompt_components if type(c) == PackageFilePromptComponent)
    return component.payload

def chain(req: XRayRequest) -> Runnable[dict, constr()]:
    chain = (
        RunnableLambda(unpack_package_file_prompt) 
        | RunnableLambda(lambda p : p.variables) 
        | PromptTemplate.from_template(unpack_package_file_prompt(req).template)
        | Anthropic(model="claude-2", temperature=0.0)
        | StrOutputParser()
    )

    return chain
