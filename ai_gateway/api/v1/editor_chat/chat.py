from typing import List, Optional, AsyncIterator, Union
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import json
import asyncio

from ai_gateway.chat.tools.base import BaseTool
from ai_gateway.models.base import connect_anthropic
from ai_gateway.models.v2.anthropic_claude import ChatAnthropic
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain.tools import BaseTool as LangChainBaseTool
from langchain.memory import ConversationBufferMemory
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.base import BaseMessageChunk
from typing import List, Union, Optional, TypedDict, Literal, Dict


router = APIRouter()


class ChatHistoryMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class AIContextItem(BaseModel):
    id: str
    category: str
    content: Optional[str] = None


def build_additional_context_prompt(
    additional_context: Optional[List[AIContextItem]],
) -> str:
    if not additional_context:
        return ""

    context_items: List[str] = []
    for item in additional_context:
        context_items.append(f"- {item.category}: {item.id}")
        if item.content:
            context_items.append(f"  Content: {item.content}")

    return "User added additional context:\n" + "\n".join(context_items)


class EditorChatRequest(BaseModel):
    prompt: str
    tools: List[BaseTool]
    openapi_schema: Optional[dict] = None
    history: Optional[List[ChatHistoryMessage]] = []
    additional_context: Optional[List[AIContextItem]] = []


async def get_anthropic_chat_model() -> ChatAnthropic:
    """
    Get the Anthropic chat model by connecting directly to the Anthropic API.
    """
    async_client = connect_anthropic()
    return ChatAnthropic(
        async_client=async_client,
        model="claude-3-5-sonnet-20240620",
        streaming=True,  # Enable streaming
    )


def convert_to_anthropic_tool(base_tool: BaseTool) -> dict:
    # Convert BaseTool to Anthropic's tool schema
    properties = {
        param.name: {"type": param.type, "description": param.description}
        for param in base_tool.parameters
        if param is not None
    }
    return {
        "name": base_tool.name,
        "description": base_tool.description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": [
                param.name
                for param in base_tool.parameters
                if param is not None and param.required
            ],
        },
    }


class CustomCallbackHandler(AsyncCallbackHandler):
    def __init__(self):
        super().__init__()
        self.queue = asyncio.Queue()

    async def aiter(self):
        while True:
            item = await self.queue.get()
            if item is None:
                break
            yield item

    async def on_llm_new_token(self, token: str, **kwargs):
        print("token", token)
        # Stream each token
        await self.queue.put(f"data: {token}\n\n")

    async def on_llm_end(self, response: AIMessage, **kwargs):
        # Send the final response
        event = {"event_type": "chat_response", "content": response.content}
        await self.queue.put(f"data: {json.dumps(event)}\n\n")
        await self.queue.put(None)


def build_sse_message(message: str) -> str:
    return f"data: {message}\n\n"


class TextContentChunk:
    def __init__(self, text: str, index: int) -> None:
        self.text = text
        self.index = index

    text: str
    index: int


class ToolUseSelected:
    def __init__(self, id: str, name: str, index: int) -> None:
        self.id = id
        self.name = name
        self.index = index

    id: str
    name: str
    index: int


class ToolUseContentChunk:
    def __init__(self, index: int, partial_json: str) -> None:
        self.index = index
        self.partial_json = partial_json

    index: int
    partial_json: str


def handle_stream_chunk(chunk: BaseMessageChunk):
    if not isinstance(chunk.content, list):
        return None
    if len(chunk.content) == 0:
        return None
    chunk_content = chunk.content[0]
    if not isinstance(chunk_content, dict):
        return None

    if chunk_content["type"] == "text":
        return TextContentChunk(
            text=chunk_content["text"], index=chunk_content["index"]
        )
    if chunk_content["type"] == "tool_use":
        if "id" and "name" in chunk_content:
            return ToolUseSelected(
                id=chunk_content["id"],
                name=chunk_content["name"],
                index=chunk_content["index"],
            )
        if "partial_json" in chunk_content:
            return ToolUseContentChunk(
                index=chunk_content["index"], partial_json=chunk_content["partial_json"]
            )
    return None


class ToolSelection(TypedDict):
    id: str
    name: str
    args: Optional[str]
    index: int


class ToolSelectionTracker:
    def __init__(self):
        self.selections: Dict[int, ToolSelection] = {}

    def add_selection(self, index: int, id: str, name: str):
        if index not in self.selections:
            self.selections[index] = {
                "id": id,
                "name": name,
                "args": None,
                "index": index,
            }
        if index in self.selections:
            self.selections[index]["id"] = id
            self.selections[index]["name"] = name
            self.selections[index]["index"] = index

    def update_args(self, index: int, args: str):
        if index in self.selections:
            if self.selections[index]["args"]:
                self.selections[index]["args"] = self.selections[index]["args"] + args
            else:
                self.selections[index]["args"] = args
        else:
            self.selections[index] = {
                "args": args,
                "id": "NA",
                "name": "NA",
                "index": index,
            }

    def get_selection(self, index: int) -> Optional[ToolSelection]:
        return self.selections.get(index)

    def get_all_selections(self) -> List[ToolSelection]:
        return list(self.selections.values())


@router.post("/chat")
async def editor_chat(
    chat_request: EditorChatRequest,
    anthropic_chat_model: ChatAnthropic = Depends(get_anthropic_chat_model),
):
    print("chat_request", chat_request)
    try:
        # Initialize memory with conversation history
        memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )

        # Add the system message indicating it's a GitLab coding agent
        system_message = SystemMessage(
            content="You are a GitLab coding agent. When selecting the tool, don't mention the tool's name. Always render in markdown."
        )
        memory.chat_memory.messages.append(system_message)

        # Load conversation history into memory
        for message in chat_request.history if chat_request.history else []:
            if message.role == "user":
                memory.chat_memory.add_user_message(
                    HumanMessage(content=message.content)
                )
            elif message.role == "assistant":
                memory.chat_memory.add_ai_message(AIMessage(content=message.content))

            # Convert tools to Anthropic format
        anthropic_tools = [
            convert_to_anthropic_tool(tool) for tool in chat_request.tools
        ]

        # Bind tools to the Anthropic model
        anthropic_chat_model = anthropic_chat_model.bind_tools(anthropic_tools)

        # Create a custom callback handler
        callback_handler = CustomCallbackHandler()

        async def stream_agent_response() -> AsyncIterator[str]:
            prompt_message = chat_request.prompt + build_additional_context_prompt(
                chat_request.additional_context
            )
            messages = memory.chat_memory.messages + [
                HumanMessage(content=prompt_message)
            ]

            stream = anthropic_chat_model.astream(
                messages,
                run_manager=callback_handler,
            )

            full_message = ""

            tool_selection_tracker = ToolSelectionTracker()

            async for raw_chunk in stream:
                print(raw_chunk, "shayon", type(raw_chunk))
                chunk = handle_stream_chunk(raw_chunk)
                if chunk:
                    if isinstance(chunk, TextContentChunk):
                        print("text content chunk", chunk)
                        message = build_sse_message(
                            json.dumps(
                                {"event_type": "message_chunk", "content": chunk.text}
                            )
                        )
                        yield message
                        full_message += chunk.text

                    if isinstance(chunk, ToolUseSelected):
                        tool_selection_tracker.add_selection(
                            chunk.index, chunk.id, chunk.name
                        )
                    if isinstance(chunk, ToolUseContentChunk):
                        tool_selection_tracker.update_args(
                            chunk.index, chunk.partial_json
                        )

            for selection in tool_selection_tracker.get_all_selections():
                print("selection", selection)
                yield build_sse_message(
                    json.dumps(
                        {
                            "event_type": "tool_chosen",
                            "name": selection["name"],
                            "args": selection["args"],
                            "index": selection["index"],
                        }
                    )
                )
            print("full_message", full_message)
            yield build_sse_message(
                json.dumps({"event_type": "full_message", "content": full_message})
            )

        return StreamingResponse(
            stream_agent_response(), media_type="text/event-stream"
        )
    except Exception as e:
        print(f"Error in editor_chat: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
