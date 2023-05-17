from time import time

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, constr

from codesuggestions.deps import CodeSuggestionsContainer
from codesuggestions.suggestions import CodeSuggestionsUseCaseV2

__all__ = [
    "router",
]

router = APIRouter(
    prefix="/completions",
    tags=["completions"],
)


class CurrentFile(BaseModel):
    file_name: constr(strip_whitespace=True, max_length=255)
    content_above_cursor: constr(max_length=100000)
    content_below_cursor: constr(max_length=100000)


class SuggestionsRequest(BaseModel):
    prompt_version: int = 1
    project_path: constr(strip_whitespace=True, max_length=255)
    project_id: int
    current_file: CurrentFile


class SuggestionsResponse(BaseModel):
    class Choice(BaseModel):
        text: str
        index: int = 0
        finish_reason: str = "length"

    id: str
    model: str = "codegen"
    object: str = "text_completion"
    created: int
    choices: list[Choice]


class CompletedSuggestionData:
    def __init__(self, request: SuggestionsRequest, response: SuggestionsResponse):
        self.request = request
        self.response = response

    def to_json(self):
        return {
            "file_data": jsonable_encoder(self.request.current_file),
            "project_path": self.request.project_path,
            "choices": jsonable_encoder(self.response.choices)
        }


@router.post("", response_model=SuggestionsResponse)
@inject
async def completions(
    raw_request: Request,
    req: SuggestionsRequest,
    code_suggestions: CodeSuggestionsUseCaseV2 = Depends(
        Provide[CodeSuggestionsContainer.usecase_v2]
    ),
):
    suggestion = code_suggestions(
        req.current_file.content_above_cursor,
        req.current_file.file_name,
    )

    response = SuggestionsResponse(
        id="id",
        created=int(time()),
        choices=[
            SuggestionsResponse.Choice(text=suggestion),
        ],
    )

    completed_suggestion = CompletedSuggestionData(req, response)
    raw_request.state.completed_suggestion = completed_suggestion

    return response
