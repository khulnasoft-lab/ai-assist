from pathlib import Path
from typing import Any, Optional

from transformers import PreTrainedTokenizer

from codesuggestions._assets import TPL_DIR
from codesuggestions.models import (
    PalmCodeGenBaseModel,
    VertexModelInternalError,
    VertexModelInvalidArgument,
)
from codesuggestions.prompts import PromptTemplate
from codesuggestions.suggestions.processing.base import (
    CodeContent,
    MetadataModel,
    MetadataPromptBuilder,
    ModelEngineBase,
    ModelEngineOutput,
    Prompt,
    PromptBuilderBase,
)
from codesuggestions.suggestions.processing.ops import (
    LanguageId,
    strip_code_block_markdown,
    truncate_content,
)

__all__ = [
    "PromptBuilder",
    "ModelEngineGenerations",
]


class PromptBuilder(PromptBuilderBase):
    def __init__(
        self, prefix: CodeContent, file_name: str, lang_id: Optional[LanguageId] = None
    ):
        super().__init__(prefix, lang_id=lang_id)

        self.file_name = file_name

    def add_template(self, tpl: PromptTemplate, **kwargs: Any):
        # We use either the language name or the file extension
        # if we couldn't determine the language before
        lang_repl = (
            self.lang_id.name.lower()
            if self.lang_id
            else Path(self.file_name).suffix.replace(".", "")
        )

        # TODO: We're not building a context right now
        # TODO: so let's put everything in the prefix as a short term solution
        self._prefix = tpl.apply(prefix=self._prefix, lang=lang_repl, **kwargs)

    def build(self) -> Prompt:
        return Prompt(
            prefix=self._prefix,
            metadata=MetadataPromptBuilder(
                components={
                    "prefix": self._metadata["prefix"],
                }
            ),
        )


class ModelEngineGenerations(ModelEngineBase):
    def __init__(
        self,
        model: PalmCodeGenBaseModel,
        tokenizer: PreTrainedTokenizer,
        tpl_version: int = 1,
    ):
        super().__init__(model, tokenizer)

        self.tpl = PromptTemplate.from_local_file(
            TPL_DIR / model.model_name / str(tpl_version) / "prompt.tpl"
        )

    async def _generate(
        self,
        prefix: str,
        _suffix: str,
        file_name: str,
        lang_id: Optional[LanguageId] = None,
        **kwargs: Any,
    ) -> ModelEngineOutput:
        model_metadata = MetadataModel(
            name=self.model.model_name, engine=self.model.model_engine
        )

        prompt = self._build_prompt(prefix, file_name, lang_id=lang_id)
        with self.instrumentator.watch(prompt) as watch_container:
            try:
                if res := await self.model.generate(prompt.prefix, "", **kwargs):
                    watch_container.register_model_output_length(res.text)
                    watch_container.register_model_score(res.score)

                    generation = strip_code_block_markdown(res.text)

                    return ModelEngineOutput(
                        text=generation,
                        model=model_metadata,
                        lang_id=lang_id,
                        metadata=prompt.metadata,
                    )

            except (VertexModelInvalidArgument, VertexModelInternalError) as ex:
                watch_container.register_model_exception(str(ex), ex.code)

        return ModelEngineOutput(text="", model=model_metadata)

    def _build_prompt(
        self, prefix: str, file_name: str, lang_id: Optional[LanguageId] = None
    ):
        # Get the length of the prompt template to truncate the prefix accordingly
        tpl_tokens = self.tokenizer(
            self.tpl.raw,
            return_attention_mask=False,
            add_special_tokens=False,
        )["input_ids"]

        prefix_truncated = truncate_content(
            self.tokenizer,
            prefix,
            max_length=self.model.MAX_MODEL_LEN - len(tpl_tokens),
            truncation_side="left",
        )

        prompt_builder = PromptBuilder(prefix_truncated, file_name, lang_id=lang_id)
        prompt_builder.add_template(self.tpl)
        prompt = prompt_builder.build()

        return prompt
