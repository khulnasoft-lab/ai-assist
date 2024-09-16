# not needed any more since we are using jinja already

# from typing import Optional, Any, cast, Sequence
#
# from langchain_core.messages import MessageLikeRepresentation
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.runnables import Runnable, RunnableBinding
#
# from ai_gateway.prompts import Prompt
# from ai_gateway.prompts.base import Input, Output
# from ai_gateway.prompts.config import PromptConfig
# from ai_gateway.prompts.typing import TypeModelFactory, ModelMetadata
#
#
# class AnthropicAgent(Prompt[Input, Output]):
#   def __init__(
#     self,
#     model_factory: TypeModelFactory,
#     config: PromptConfig,
#     model_metadata: Optional[ModelMetadata] = None,
#   ):
#     model_kwargs = self._build_model_kwargs(config.params, model_metadata)
#     model = self._build_model(model_factory, config.model)
#     messages = self.build_messages(config.prompt_template)
#     prompt = ChatPromptTemplate.from_messages(messages, template_format='jinja2')
#     chain = self._build_chain(
#       cast(Runnable[Input, Output], prompt | model.bind(**model_kwargs))
#     )
#
#     # skip prompt's init method, use Prompt's parent class's init method
#     super(Prompt, self).__init__(
#       name=config.name,
#       model=model,
#       prmpt=prompt,  # TODO: remove this, it's to print rendered prompt in pdb
#       unit_primitives=config.unit_primitives,
#       bound=chain,
#     )  # type: ignore[call-arg]
#
#   @classmethod
#   def build_messages(cls,prompt_template: dict[str, str]) -> Sequence[MessageLikeRepresentation]:
#     messages = []
#
#     for role, template in cls._prompt_template_to_messages(tpl=prompt_template):
#         messages.append((role,template))
#
#     return messages
