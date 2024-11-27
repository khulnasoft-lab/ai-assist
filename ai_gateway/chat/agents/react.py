import re
from typing import Any, AsyncIterator, Optional, Sequence

import starlette_context
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import BaseCumulativeTransformOutputParser
from langchain_core.outputs import Generation
from langchain_core.prompts.chat import MessageLikeRepresentation
from langchain_core.runnables import Runnable, RunnableConfig
from pydantic import BaseModel

from ai_gateway.chat.agents.typing import (
    AgentError,
    AgentFinalAnswer,
    AgentStep,
    AgentToolAction,
    AgentUnknownAction,
    Message,
    TypeAgentEvent,
)
from ai_gateway.chat.tools.base import BaseTool
from ai_gateway.models.base_chat import Role
from ai_gateway.prompts import Prompt, jinja2_formatter
from ai_gateway.prompts.typing import ModelMetadata

__all__ = [
    "ReActAgentInputs",
    "ReActPlainTextParser",
    "ReActAgent",
]

from ai_gateway.structured_logging import get_request_logger

_REACT_AGENT_TOOL_ACTION_CONTEXT_KEY = "duo_chat.agent_tool_action"

request_log = get_request_logger("react")


class ReActAgentInputs(BaseModel):
    messages: list[Message]
    agent_scratchpad: Optional[list[AgentStep]] = None
    model_metadata: Optional[ModelMetadata] = None
    unavailable_resources: Optional[list[str]] = None
    tools: Optional[list[BaseTool]] = None


class ReActPlainTextParser(BaseCumulativeTransformOutputParser):
    re_thought: re.Pattern = re.compile(
        r"<message>Thought:\s*([\s\S]*?)\s*(?:Action|Final Answer):"
    )
    re_action: re.Pattern = re.compile(r"Action:\s*([\s\S]*?)\s*Action", re.DOTALL)
    re_action_input: re.Pattern = re.compile(r"Action Input:\s*([\s\S]*?)\s*</message>")
    re_final_answer: re.Pattern = re.compile(r"Final Answer:\s*([\s\S]*?)\s*</message>")

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
            tool_name = match_action.group(1)
            return AgentToolAction(
                tool=self._modify_tool_name(tool_name),
                tool_input=match_action_input.group(1),
                thought=(
                    match_thought.group(1).replace("\\_", "_") if match_thought else ""
                ),
            )

        return None

    def _modify_tool_name(self, name: str) -> str:
        """Process special case when LLM returns wrong name

        In some cases LLM could return the name of the Merge Request tool
        in CamelCase, not in underscore_case.
        This bug was fixed in upstream version of GitLab 17.7
        However older GitLab instances could still have this bug.
        Would be cleaned up with
        https://gitlab.com/gitlab-org/modelops/applied-ml/code-suggestions/ai-assist/-/issues/757
        """
        if name == "MergeRequestReader":
            return "merge_request_reader"

        return name.replace("\\_", "_")

    def _parse_native_tool_call_action(
        self, message: str, result: Any
    ) -> Optional[AgentToolAction]:
        response_meta = result[0].message.response_metadata
        if not response_meta or response_meta.get("stop_reason") != "tool_use":
            return None

        tool_call = result[0].message.tool_calls[0]
        args = tool_call["args"]

        return AgentToolAction(
            tool=args["action"].replace("\\_", "_", 1),
            tool_input=args["action_input"],
            thought=args["thought"].replace("\\_", "_") if args.get("thought") else "",
        )

    def _parse_base(self, text: str, parse_action_fn, **kwargs) -> TypeAgentEvent:
        wrapped_text = f"<message>Thought: {text}</message>"

        event: Optional[TypeAgentEvent] = None
        if final_answer := self._parse_final_answer(wrapped_text):
            event = final_answer
        elif agent_action := parse_action_fn(wrapped_text, **kwargs):
            event = agent_action
        else:
            event = AgentUnknownAction(text=text)

        return event

    def _parse(self, text: str) -> TypeAgentEvent:
        return self._parse_base(text, self._parse_agent_action)

    def _parse_native_tool_call(self, text: str, result: Any) -> TypeAgentEvent:
        return self._parse_base(
            text, self._parse_native_tool_call_action, result=result
        )

    def parse_result(
        self, result: list[Generation], *, partial: bool = False
    ) -> Optional[TypeAgentEvent]:
        event = None
        text = result[0].text.strip()

        try:
            if result[0].message.tool_calls:
                event = self._parse_native_tool_call(text, result)
            else:
                event = self._parse(text)

        except ValueError as e:
            if not partial:
                msg = f"Invalid output: {text}"
                raise OutputParserException(msg, llm_output=text) from e

        return event

    def parse(self, text: str) -> Optional[TypeAgentEvent]:
        return self.parse_result([Generation(text=text)])


class ReActAgent(Prompt[ReActAgentInputs, TypeAgentEvent]):
    RETRYABLE_ERRORS: list[str] = ["overloaded_error"]

    @staticmethod
    def _build_chain(
        chain: Runnable[ReActAgentInputs, TypeAgentEvent]
    ) -> Runnable[ReActAgentInputs, TypeAgentEvent]:
        return chain | ReActPlainTextParser()

    @classmethod
    def build_messages(
        cls,
        prompt_template: dict[str, str],
        agent_inputs: ReActAgentInputs,
        **kwargs,
    ) -> Sequence[MessageLikeRepresentation]:
        messages = []

        if "system" in prompt_template:
            messages.append(
                SystemMessage(
                    jinja2_formatter(
                        prompt_template["system"],
                        tools=agent_inputs.tools,
                        unavailable_resources=agent_inputs.unavailable_resources,
                    )
                )
            )

        for m in agent_inputs.messages:
            if m.role is Role.USER:
                messages.append(
                    HumanMessage(jinja2_formatter(prompt_template["user"], message=m))
                )
            elif m.role is Role.ASSISTANT:
                messages.append(AIMessage(m.content))
            else:
                raise ValueError("Unsupported message")

        if not isinstance(messages[-1], HumanMessage):
            raise ValueError("Last message must be a human message")

        messages.append(
            AIMessage(
                jinja2_formatter(
                    prompt_template["assistant"],
                    agent_scratchpad=agent_inputs.agent_scratchpad,
                )
            )
        )

        # TODO - fix this
        #  Temporary to fix "Your API request included an `assistant` message in the final
        #  position, which would pre-fill the `assistant` response. When using tools, pre-filling the `assistant`
        #  response is not supported"
        messages.append(HumanMessage("Continue from the previous steps"))
        return messages

    async def astream(
        self,
        config: Optional[RunnableConfig] = None,
        **kwargs: Optional[Any],
    ) -> AsyncIterator[TypeAgentEvent]:
        events = []
        astream = super().astream(config=config, **kwargs)
        len_final_answer = 0

        try:
            async for event in astream:
                request_log.info(
                    "Response streaming", source=__name__, streamed_event=event
                )

                if isinstance(event, AgentFinalAnswer) and len(event.text) > 0:
                    yield AgentFinalAnswer(
                        text=event.text[len_final_answer:],
                    )

                    len_final_answer = len(event.text)

                events.append(event)
        except Exception as e:
            error_message = str(e)
            retryable = any(err in error_message for err in self.RETRYABLE_ERRORS)

            yield AgentError(message=error_message, retryable=retryable)
            raise

        if any(isinstance(e, AgentFinalAnswer) for e in events):
            pass  # no-op
        elif any(isinstance(e, AgentToolAction) for e in events):
            event = events[-1]
            starlette_context.context[_REACT_AGENT_TOOL_ACTION_CONTEXT_KEY] = event.tool
            yield event
        elif isinstance(events[-1], AgentUnknownAction):
            yield events[-1]
