from typing import List, Optional, AsyncIterator, Union
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError
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
from langchain_core.messages.ai import AIMessageChunk


router = APIRouter()


class AIContextItem(BaseModel):
    id: str
    category: str
    content: Optional[str] = None


class ChatHistoryMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    additional_context: Optional[List[AIContextItem]] = []
    tool_used: bool = False


def build_additional_context_prompt(
    additional_context: Optional[List[AIContextItem]], tool_used: bool = False
) -> str:
    if not additional_context:
        return ""

    context_items: List[str] = []
    for item in additional_context:
        context_items.append(f"- {item.category}: {item.id}")
        if item.content:
            context_items.append(f"  Content: {item.content}")

    if tool_used:
        return "Tool context:\n" + "\n".join(context_items)
    else:
        return "User added additional context:\n" + "\n".join(context_items)


class EditorChatRequest(BaseModel):
    prompt: str
    tools: List[BaseTool]
    openapi_schema: Optional[dict] = None
    history: Optional[List[ChatHistoryMessage]] = []
    additional_context: Optional[List[AIContextItem]] = []
    tool_used: bool = False


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
    properties = {}
    for param in base_tool.parameters:
        if param is not None:
            param_info = {"type": param.type, "description": param.description}
            if param.type == "array" and hasattr(param, "items"):
                param_info["items"] = param.items
            properties[param.name] = param_info

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
        for history_message in chat_request.history if chat_request.history else []:
            if history_message.role == "user":
                human_message = (
                    history_message.content
                    + build_additional_context_prompt(
                        history_message.additional_context, history_message.tool_used
                    )
                )
                memory.chat_memory.add_user_message(HumanMessage(content=human_message))
            elif history_message.role == "assistant":
                memory.chat_memory.add_ai_message(
                    AIMessage(content=history_message.content)
                )

            # Convert tools to Anthropic format
        anthropic_tools = [
            convert_to_anthropic_tool(tool) for tool in chat_request.tools
        ]
        print("anthropic_tools", anthropic_tools)

        # Bind tools to the Anthropic model
        anthropic_chat_model = anthropic_chat_model.bind_tools(anthropic_tools)

        # Create a custom callback handler
        callback_handler = CustomCallbackHandler()

        async def stream_agent_response() -> AsyncIterator[str]:
            prompt_message = chat_request.prompt + build_additional_context_prompt(
                chat_request.additional_context, chat_request.tool_used
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

            total_tokens = 0
            async for raw_chunk in stream:
                chunk = handle_stream_chunk(raw_chunk)
                if isinstance(raw_chunk, AIMessageChunk):
                    usage_metadata = raw_chunk.usage_metadata
                    if usage_metadata:
                        total_tokens += usage_metadata.get("input_tokens", 0)
                        total_tokens += usage_metadata.get("output_tokens", 0)
                if chunk:
                    if isinstance(chunk, TextContentChunk):
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
            yield build_sse_message(
                json.dumps({"event_type": "tokens_count", "total_tokens": total_tokens})
            )
            yield build_sse_message(
                json.dumps({"event_type": "full_message", "content": full_message})
            )

        return StreamingResponse(
            stream_agent_response(), media_type="text/event-stream"
        )
    except Exception as e:
        print(f"Error in editor_chat: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


class ChatSummaryRequest(BaseModel):
    history: List[ChatHistoryMessage]
    type: Optional[Literal["summary", "questions"]] = "summary"
    max_title_length: int = Field(default=50, ge=1, le=100)
    max_description_length: int = Field(default=200, ge=1, le=500)


class ChatSummaryResponse(BaseModel):
    title: str
    description: str


class ChatQuestionsResponse(BaseModel):
    questions: List[str]


class ChatSummary(BaseModel):
    """Summary of a chat conversation."""

    title: str = Field(
        ...,
        description="A concise title summarizing the main topic of the conversation",
    )
    description: str = Field(
        ...,
        description="A brief description summarizing the key points of the conversation",
    )


class ChatQuestions(BaseModel):
    """Questions from a chat conversation."""

    questions: List[str] = Field(
        ...,
        description="A list of questions that capture the key points of the conversation",
    )


@router.post(
    "/chat/summary", response_model=Union[ChatSummaryResponse, ChatQuestionsResponse]
)
async def chat_summary(
    summary_request: ChatSummaryRequest,
    anthropic_chat_model: ChatAnthropic = Depends(get_anthropic_chat_model),
):
    try:
        # Prepare the chat history
        chat_history = []
        for msg in summary_request.history:
            role = "Human" if msg.role == "user" else "Assistant"
            content = msg.content
            if msg.additional_context:
                content += "\n" + build_additional_context_prompt(
                    msg.additional_context, msg.tool_used
                )
            chat_history.append(f"{role}: {content}")

        if summary_request.type == "summary":
            # Create the prompt for summarization
            prompt = (
                "Based on the following chat history, generate a concise title and a brief description "
                "that summarizes the main topic and key points of the conversation:\n\n"
                f"Chat History:\n{chr(10).join(chat_history)}\n\n"
                f"Please provide a title (max {summary_request.max_title_length} characters) and a description "
                f"(max {summary_request.max_description_length} characters) that capture the essence of this conversation."
            )

            # Bind the ChatSummary tool to the model
            llm_with_summary_tool = anthropic_chat_model.bind_tools([ChatSummary])

            # Invoke the model with the prompt
            response = await llm_with_summary_tool.ainvoke(
                [HumanMessage(content=prompt)]
            )

            # Extract the summary from the response
            tool_calls = response.tool_calls
            if tool_calls and len(tool_calls) > 0:
                summary = tool_calls[0].get("args", {})
            else:
                return JSONResponse(
                    content={"error": "No tool calls found in response"},
                    status_code=500,
                )

            try:
                parsed_summary = ChatSummary(**summary)
            except ValidationError as e:
                print(f"Validation error: {e}")
                return JSONResponse(content={"error": str(e)}, status_code=400)

            return ChatSummaryResponse(
                title=parsed_summary.title[: summary_request.max_title_length],
                description=parsed_summary.description[
                    : summary_request.max_description_length
                ],
            )
        elif summary_request.type == "questions":
            print("summary_request.type", summary_request.type)
            # Create the prompt for summarization
            prompt = (
                f"You are a GitLab coding agent."
                f"Chat History:\n```\n{chr(10).join(chat_history)}\n\n```"
                f"Please provide a list of 5 prompts that a user might ask a GitLab coding agent based on the Chat History."
                f"If the data contains references to a web framework, frame the prompts in terms of that framework."
                f"Frame the prompts from the perspective of the user, not the AI."
            )
            print("prompt", prompt)

            # Bind the ChatQuestions tool to the model
            llm_with_questions_tool = anthropic_chat_model.bind_tools([ChatQuestions])

            # Invoke the model with the prompt
            response = await llm_with_questions_tool.ainvoke(
                [HumanMessage(content=prompt)]
            )

            # Extract the questions from the response
            tool_calls = response.tool_calls

            if tool_calls and len(tool_calls) > 0:
                questions = tool_calls[0].get("args", {})
            else:
                return JSONResponse(
                    content={"error": "No tool calls found in response"},
                    status_code=500,
                )

            try:
                parsed_questions = ChatQuestions(**questions)
            except ValidationError as e:
                print(f"Validation error: {e}")
                return JSONResponse(content={"error": str(e)}, status_code=400)

            return ChatQuestionsResponse(questions=parsed_questions.questions)

    except Exception as e:
        print(f"Error in chat_summary: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
