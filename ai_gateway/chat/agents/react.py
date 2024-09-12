import re
from typing import Any, AsyncIterator, Optional

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import BaseCumulativeTransformOutputParser
from langchain_core.outputs import Generation
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from pydantic import BaseModel

from ai_gateway.auth import GitLabUser
from ai_gateway.chat.agents.typing import (
    AdditionalContext,
    AgentFinalAnswer,
    AgentStep,
    AgentToolAction,
    AgentUnknownAction,
    Context,
    CurrentFile,
    TypeAgentEvent,
)
from ai_gateway.chat.tools.base import BaseTool
from ai_gateway.chat.toolset import DuoChatToolsRegistry
from ai_gateway.models.base_chat import Message
from ai_gateway.prompts import Prompt, LocalPromptRegistry
from ai_gateway.prompts.typing import ModelMetadata

__all__ = [
    "ReActAgentInputs",
    "ReActPlainTextParser",
    "ReActAgent",
]


class ReActAgentInputs(BaseModel):
    question: str
    chat_history: str | list[str]
    agent_scratchpad: list[AgentStep]
    user: GitLabUser
    gl_version: str
    context: Optional[Context] = None
    current_file: Optional[CurrentFile] = None
    model_metadata: Optional[ModelMetadata] = None
    additional_context: Optional[list[AdditionalContext]] = None
    unavailable_resources: Optional[list[str]] = [
        "Merge Requests",
        "Pipelines",
        "Vulnerabilities",
    ]
    tools: Optional[list[BaseTool]] = None


class ReActInputParser(Runnable[ReActAgentInputs, dict]):
    def invoke(
        self, input: ReActAgentInputs, config: Optional[RunnableConfig] = None
    ) -> dict:
        final_inputs = {
            "additional_context": input.additional_context,
            "context_type": "",
            "context_content": "",
            "question": input.question,
            "agent_scratchpad": agent_scratchpad_plain_text_renderer(
                input.agent_scratchpad
            ),
            "current_file": input.current_file,
            "unavailable_resources": input.unavailable_resources,
            "tools": input.tools,
        }

        if isinstance(input.chat_history, list) and isinstance(
            input.chat_history[0], Message
        ):
            final_inputs["chat_history"] = input.chat_history
        else:
            final_inputs["chat_history"] = chat_history_plain_text_renderer(
                input.chat_history
            )

        if context := input.context:
            final_inputs.update(
                {"context_type": context.type, "context_content": context.content}
            )

        return final_inputs


def chat_history_plain_text_renderer(chat_history: list | str) -> str:
    if isinstance(chat_history, list):
        return "\n".join(chat_history)

    return chat_history


def agent_scratchpad_plain_text_renderer(
    scratchpad: list[AgentStep],
) -> str:
    tpl = (
        "Thought: {thought}\n"
        "Action: {action}\n"
        "Action Input: {action_input}\n"
        "Observation: {observation}"
    )

    steps = [
        tpl.format(
            thought=pad.action.thought,
            action=pad.action.tool,
            action_input=pad.action.tool_input,
            observation=pad.observation,
        )
        for pad in scratchpad
        if isinstance(pad.action, AgentToolAction)
    ]

    return "\n".join(steps)


class ReActPlainTextParser(BaseCumulativeTransformOutputParser):
    re_thought = re.compile(
        r"<message>Thought:\s*([\s\S]*?)\s*(?:Action|Final Answer):"
    )
    re_action = re.compile(r"Action:\s*([\s\S]*?)\s*Action", re.DOTALL)
    re_action_input = re.compile(r"Action Input:\s*([\s\S]*?)\s*</message>")
    re_final_answer = re.compile(r"Final Answer:\s*([\s\S]*?)\s*</message>")

    def _parse_final_answer(self, message: str) -> Optional[AgentFinalAnswer]:
        if match_answer := self.re_final_answer.search(message):
            match_thought = self.re_thought.search(message)

            return AgentFinalAnswer(
                thought=match_thought.group(1) if match_thought else "",
                text=match_answer.group(1),
            )

        return None

    def _parse_agent_action(self, message: str) -> Optional[AgentToolAction]:
        match_action = self.re_action.search(message)
        match_action_input = self.re_action_input.search(message)
        match_thought = self.re_thought.search(message)

        if match_action and match_action_input:
            return AgentToolAction(
                tool=match_action.group(1),
                tool_input=match_action_input.group(1),
                thought=match_thought.group(1) if match_thought else "",
            )

        return None

    def _parse(self, text: str) -> TypeAgentEvent:
        wrapped_text = f"<message>Thought: {text}</message>"

        event: Optional[TypeAgentEvent] = None
        if final_answer := self._parse_final_answer(wrapped_text):
            event = final_answer
        elif agent_action := self._parse_agent_action(wrapped_text):
            event = agent_action
        else:
            event = AgentUnknownAction(text=text)

        return event

    def parse_result(
        self, result: list[Generation], *, partial: bool = False
    ) -> Optional[TypeAgentEvent]:
        event = None
        text = result[0].text.strip()

        try:
            event = self._parse(text)
        except ValueError as e:
            if not partial:
                msg = f"Invalid output: {text}"
                raise OutputParserException(msg, llm_output=text) from e

        return event

    def parse(self, text: str) -> Optional[TypeAgentEvent]:
        return self.parse_result([Generation(text=text)])


class ReActAgent:
    def __init__(self, prompt_registry: LocalPromptRegistry, tools_registry: DuoChatToolsRegistry):
        self.chain = chain
        self.tools_registry = tools_registry

    @staticmethod
    def _build_chain(
        chain: Runnable[ReActAgentInputs, TypeAgentEvent]
    ) -> Runnable[ReActAgentInputs, TypeAgentEvent]:
        return ReActInputParser() | chain | ReActPlainTextParser()

    @classmethod
    def build_prompt(cls, prompt_template: dict[str, str]) -> ChatPromptTemplate:
        messages = []

        for role, template in cls._prompt_template_to_messages(prompt_template):
            messages.append((role, template))

        prompt = ChatPromptTemplate.from_messages(messages, template_format="jinja2")

        return prompt

    async def astream(self, input: ReActAgentInputs) -> AsyncIterator[TypeAgentEvent]:
        events = []

        self._tools = self.tools_registry.get_on_behalf(input.user, input.gl_version)

        astream = self.chain.astream(input, config=config, **kwargs)
        len_final_answer = 0

        async for event in astream:
            if isinstance(event, AgentFinalAnswer) and len(event.text) > 0:
                yield AgentFinalAnswer(
                    text=event.text[len_final_answer:],
                )

                len_final_answer = len(event.text)

            events.append(event)

        if any(isinstance(e, AgentFinalAnswer) for e in events):
            pass  # no-op
        elif any(isinstance(e, AgentToolAction) for e in events):
            yield events[-1]
        elif isinstance(events[-1], AgentUnknownAction):
            yield events[-1]
