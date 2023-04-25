from enum import Enum
from typing import List

from codesuggestions.models import PalmTextGenBaseModel, TextGenModelOutput

__all__ = [
    "PalmUseCaseObjective",
    "PalmTextGenUseCase",
]


class PalmUseCaseObjective(Enum):
    TEXT = 1


class PalmTextGenUseCase:
    def __init__(self, text_model: PalmTextGenBaseModel):
        self.text_model = text_model

    @property
    def objective(self) -> PalmUseCaseObjective:
        return PalmUseCaseObjective.TEXT

    def __call__(self, content: str, **kwargs) -> List[TextGenModelOutput]:
        generated = self.text_model.generate(content, **kwargs)
        return [
            generated
        ]
