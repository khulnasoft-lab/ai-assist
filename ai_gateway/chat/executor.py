from typing import AsyncIterator, Generic, Protocol

from langchain_core.runnables import Runnable

from ai_gateway.auth import GitLabUser
from ai_gateway.chat.agents import TypeAgentEvent, TypeAgentInputs
from ai_gateway.chat.base import BaseToolsRegistry
from ai_gateway.chat.tools import BaseTool
from ai_gateway.prompts import Prompt
from ai_gateway.prompts.typing import ModelMetadata

__all__ = [
    "TypeAgentFactory",
    "GLAgentRemoteExecutor",
]


class TypeAgentFactory(Protocol[TypeAgentInputs, TypeAgentEvent]):
    def __call__(
        self,
        *,
        model_metadata: ModelMetadata,
    ) -> Runnable[TypeAgentInputs, TypeAgentEvent]: ...


class GLAgentRemoteExecutor(Generic[TypeAgentInputs, TypeAgentEvent]):
    def __init__(
        self,
        *,
        chain_factory: TypeAgentFactory,
        tools_registry: BaseToolsRegistry,
    ):
        self.chain_factory = chain_factory
        self.tools_registry = tools_registry
        self._tools: list[BaseTool] | None = None

    @property
    def tools(self) -> list[BaseTool]:
        if self._tools is None:
            self._tools = self.tools_registry.get_all()

        return self._tools

    def on_behalf(self, user: GitLabUser, gl_version: str):
        # Access the user tools as soon as possible to raise an exception
        # (in case of invalid unit primitives) before starting the data stream.
        # Reason: https://github.com/tiangolo/fastapi/discussions/10138
        if not user.is_debug:
            self._tools = self.tools_registry.get_on_behalf(user, gl_version)

    async def invoke(self, *, inputs: TypeAgentInputs) -> TypeAgentEvent:
        agent, inputs = self._process_inputs(inputs)

        return await agent.ainvoke(inputs)

    async def stream(self, *, inputs: TypeAgentInputs) -> AsyncIterator[TypeAgentEvent]:
        chain, inputs = self._compose_chain(inputs)

        async for action in chain.astream(inputs):
            yield action

    def _compose_chain(self, inputs: TypeAgentInputs) -> tuple[Prompt, TypeAgentInputs]:
        chain = self.chain_factory(model_metadata=inputs.model_metadata)
        inputs.tools = self.tools

        return chain, inputs
