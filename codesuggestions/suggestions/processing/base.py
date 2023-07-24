import json
from pathlib import Path
from typing import Any, Optional, NamedTuple
from abc import ABC, abstractmethod
from enum import Enum

from prometheus_client import Counter

__all__ = [
    "LanguageId",
    "MetadataCodeContent",
    "MetadataImports",
    "MetadataPromptBuilder",
    "ModelEngineOutput",
    "MetadataModel",
    "ModelEngineBase",
]

LANGUAGE_COUNTER = Counter('code_suggestions_prompt_language', 'Language count by number', ['lang', 'extension'])

CODE_SYMBOL_COUNTER = Counter('code_suggestions_prompt_symbols', 'Prompt symbols count', ['lang', 'symbol'])


class LanguageId(Enum):
    C = 1
    CPP = 2
    CSHARP = 3
    GO = 4
    JAVA = 5
    JS = 6
    PHP = 7
    PYTHON = 8
    RUBY = 9
    RUST = 10
    SCALA = 11
    TS = 12
    KOTLIN = 13


class MetadataCodeContent(NamedTuple):
    length: int
    length_tokens: int


class MetadataImports(NamedTuple):
    pre: MetadataCodeContent
    post: MetadataCodeContent


class MetadataPromptBuilder(NamedTuple):
    prefix: MetadataCodeContent
    suffix: MetadataCodeContent
    imports: Optional[MetadataImports] = None


class MetadataModel(NamedTuple):
    name: str
    engine: str


class ModelEngineOutput(NamedTuple):
    text: str
    model: MetadataModel
    lang_id: Optional[LanguageId] = None
    metadata: Optional[MetadataPromptBuilder] = None


class ModelEngineBase(ABC):
    @abstractmethod
    async def generate_completion(self, prefix: str, suffix: str, file_name: str, **kwargs: Any) -> ModelEngineOutput:
        pass

    def increment_lang_counter(self, filename: str, lang_id: Optional[LanguageId] = None):
        labels = {'lang': None}

        if lang_id:
            labels['lang'] = lang_id.name.lower()

        labels['extension'] = Path(filename).suffix[1:]

        LANGUAGE_COUNTER.labels(**labels).inc()

    def increment_code_symbol_counter(self, lang_id: LanguageId, symbol_map: dict):
        for symbol, count in symbol_map.items():
            CODE_SYMBOL_COUNTER.labels(lang=lang_id.name.lower(), symbol=symbol).inc(count)

    @staticmethod
    def _read_json(filepath: Path) -> dict[str, list]:
        with open(str(filepath), "r") as f:
            return json.load(f)
