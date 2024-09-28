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

router = APIRouter()


class ChatHistoryMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: Union[str, List[dict]]


class EditorChatRequest(BaseModel):
    prompt: str
    tools: List[BaseTool]
    openapi_schema: Optional[dict] = None
    history: Optional[List[ChatHistoryMessage]] = []


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
    return {
        "name": base_tool.name,
        "description": base_tool.description,
        "input_schema": {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Input for the tool"}
            },
            "required": ["input"],
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

    async def on_tool_use(self, tool_name: str, tool_input: dict, **kwargs):
        print("nikilesh", tool_name, tool_input)
        # Send the "tool_chosen" event
        event = {
            "event_type": "tool_chosen",
            "tool": tool_name,
            "content": tool_input,  # The tool's input parameters
        }
        await self.queue.put(f"data: {json.dumps(event)}\n\n")

    async def on_llm_end(self, response: AIMessage, **kwargs):
        # Send the final response
        event = {"event_type": "chat_response", "content": response.content}
        await self.queue.put(f"data: {json.dumps(event)}\n\n")
        await self.queue.put(None)


@router.post("/chat")
async def editor_chat(
    chat_request: EditorChatRequest,
    anthropic_chat_model: ChatAnthropic = Depends(get_anthropic_chat_model),
):
    try:
        # Initialize memory with conversation history
        memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )

        # Add the system message indicating it's a GitLab coding agent
        system_message = SystemMessage(content="You are a GitLab coding agent. When selecting the tool, don't mention the tool's name")
        memory.chat_memory.messages.append(system_message)

        # Load conversation history into memory
        for message in chat_request.history:
            if message.role == "user":
                memory.chat_memory.add_user_message(message.content)
            elif message.role == "assistant":
                memory.chat_memory.add_ai_message(message.content)

        # Convert tools to Anthropic format
        anthropic_tools = [
            convert_to_anthropic_tool(tool) for tool in chat_request.tools
        ]

        # Bind tools to the Anthropic model
        anthropic_chat_model = anthropic_chat_model.bind_tools(anthropic_tools)

        # Create a custom callback handler
        callback_handler = CustomCallbackHandler()

        async def stream_agent_response() -> AsyncIterator[str]:
            # Prepare the messages
            messages = memory.chat_memory.messages + [
                HumanMessage(content=chat_request.prompt)
            ]

            # Run the model asynchronously with streaming
            stream = anthropic_chat_model.astream(
                messages,
                # Note: We need to pass run_manager to handle callbacks
                run_manager=callback_handler,
            )

            # Iterate over the stream and handle the chunks
            async for chunk in stream:
                if chunk.content:
                    await callback_handler.on_llm_new_token(chunk.content)
                if chunk.additional_kwargs.get("tool_calls"):
                    for tool_call in chunk.additional_kwargs["tool_calls"]:
                        await callback_handler.on_tool_use(
                            tool_name=tool_call["name"], tool_input=tool_call["args"]
                        )

            # Signal that the stream is finished
            await callback_handler.on_llm_end(chunk)

            # Yield items from the callback handler's queue
            async for item in callback_handler.aiter():
                print("shayon", item)
                yield item

        return StreamingResponse(
            stream_agent_response(), media_type="text/event-stream"
        )
    except Exception as e:
        print(f"Error in editor_chat: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
