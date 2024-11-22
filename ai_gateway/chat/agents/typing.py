import json
from typing import Literal, Optional, TypeVar

from pydantic import BaseModel

from ai_gateway.models.base_chat import Role
from ai_gateway.chat.context.current_page import PageContext

__all__ = [
    "AgentToolAction",
    "AgentFinalAnswer",
    "AgentUnknownAction",
    "AgentError",
    "AgentBaseEvent",
    "TypeAgentEvent",
    "AgentStep",
    "TypeAgentInputs",
    "CurrentFile",
    "AdditionalContext",
    "Message",
]


class AgentBaseEvent(BaseModel):
    def dump_as_response(self) -> str:
        model_dump = self.model_dump()
        type = model_dump.pop("type")
        return json.dumps({"type": type, "data": model_dump})


class AgentToolAction(AgentBaseEvent):
    type: str = "action"
    tool: str
    tool_input: str
    thought: str


class AgentFinalAnswer(AgentBaseEvent):
    type: str = "final_answer_delta"
    text: str


class AgentUnknownAction(AgentBaseEvent):
    type: str = "unknown"
    text: str


class AgentError(AgentBaseEvent):
    type: str = "error"
    message: str
    retryable: bool


TypeAgentEvent = TypeVar(
    "TypeAgentEvent", AgentToolAction, AgentFinalAnswer, AgentUnknownAction
)

TypeAgentInputs = TypeVar("TypeAgentInputs")


class AgentStep(BaseModel):
    action: AgentToolAction
    observation: str


class CurrentFile(BaseModel):
    file_path: str
    data: str
    selected_code: bool


# Note: additionaL_context is an alias for injected_context
class AdditionalContext(BaseModel):
    category: Literal["file", "snippet", "merge_request", "issue", "dependency"]
    id: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[dict] = None


class Message(BaseModel):
    role: Role
    content: str
    context: Optional[PageContext] = None
    current_file: Optional[CurrentFile] = None
    additional_context: Optional[list[AdditionalContext]] = None
