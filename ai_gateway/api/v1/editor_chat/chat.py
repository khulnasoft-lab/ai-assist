from typing import List, Optional, AsyncIterator
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import json
import asyncio

from ai_gateway.chat.tools.base import BaseTool
from ai_gateway.models.base import connect_anthropic
from ai_gateway.models.v2.anthropic_claude import ChatAnthropic
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import AgentAction, AgentFinish
from langchain.schema import SystemMessage

router = APIRouter()

class ChatHistoryMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

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
        model_name="claude-3-sonnet-20240229"
    )

def convert_to_langchain_tool(base_tool: BaseTool) -> Tool:
    def tool_func(input: str) -> str:
        # This function returns the tool name and input
        return f"{base_tool.name}|{input}"

    return Tool(
        name=base_tool.name,
        description=base_tool.description,
        func=tool_func,
    )

def create_agent(model: ChatAnthropic, tools: List[BaseTool], memory):
    # Convert the tools to LangChain Tools
    langchain_tools = [convert_to_langchain_tool(tool) for tool in tools]

    # Hardcoded system message indicating it's a GitLab coding agent
    agent_kwargs = {
        "system_message": "You are a GitLab coding agent."
    }

    agent = initialize_agent(
        tools=langchain_tools,
        llm=model,
        agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
        verbose=True,
        memory=memory,
        agent_kwargs=agent_kwargs,
    )

    return agent


class CustomCallbackHandler(AsyncCallbackHandler):
    def __init__(self):
        super().__init__()
        self.queue = asyncio.Queue()
        self.tool_selected = False

    async def aiter(self):
        while True:
            item = await self.queue.get()
            if item is None:
                break
            yield item

    async def on_llm_new_token(self, token: str, **kwargs):
        print("token", token)
        await self.queue.put(f"data: {token}\n\n")

    async def on_agent_action(self, action: AgentAction, **kwargs):
        # This method is called when the agent decides to use a tool
        self.tool_selected = True
        # Send the "tool_chosen" event
        event = {
            "event_type": "tool_chosen",
            "tool": action.tool,
            "content": action.log  # The agent's thoughts
        }
        await self.queue.put(f"data: {json.dumps(event)}\n\n")

    async def on_agent_finish(self, finish: AgentFinish, **kwargs):
        if not self.tool_selected:
            # Agent didn't use a tool, send the final response
            event = {
                "event_type": "chat_response",
                "content": finish.return_values.get("output", "")
            }
            await self.queue.put(f"data: {json.dumps(event)}\n\n")
        # Signal that the stream is finished
        await self.queue.put(None)

@router.post("/chat")
async def editor_chat(
    chat_request: EditorChatRequest,
    anthropic_chat_model: ChatAnthropic = Depends(get_anthropic_chat_model),
):
    try:
        # Initialize memory with conversation history
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)


        # Load conversation history into memory
        for message in chat_request.history:
            if message.role == "user":
                memory.chat_memory.add_user_message(message.content)
            elif message.role == "assistant":
                memory.chat_memory.add_ai_message(message.content)

        # Create a custom callback handler
        callback_handler = CustomCallbackHandler()

        # Create the agent
        agent = create_agent(anthropic_chat_model, chat_request.tools, memory)

        async def stream_agent_response() -> AsyncIterator[str]:
            # Run the agent asynchronously
            task = asyncio.create_task(agent.arun(chat_request.prompt, callbacks=[callback_handler]))

            # Iterate over the callback handler's generator
            async for item in callback_handler.aiter():
                yield item

            # Wait for the task to complete
            await task

        return StreamingResponse(stream_agent_response(), media_type="text/event-stream")
    except Exception as e:
        print(f"Error in editor_chat: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
