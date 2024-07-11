import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from ai_gateway.api.feature_category import feature_category
from ai_gateway.gitlab_features import GitLabFeatureCategory

from ai_gateway.code_suggestions.prompts.parsers import CodeParser
from ai_gateway.code_suggestions.processing.ops import lang_from_filename

__all__ = [
    "router",
]

class Blob(BaseModel):
    content: str
    line: int
    filename: str

log = structlog.stdlib.get_logger("codesuggestions")

router = APIRouter()


@router.post("/chunk")
@feature_category(GitLabFeatureCategory.CODE_SUGGESTIONS)
async def chunk(blobs: list[Blob]):
    list = []

    for blob in blobs:
        content = blob.content
        line = blob.line
        filename = blob.filename

        lang_id = lang_from_filename(filename)

        if lang_id is not None:
            parser = await CodeParser.from_language_id(content, lang_id)
            function_body_for_line = parser.function_signature_bodies(line)
        else:
            function_body_for_line = None

        list.append(function_body_for_line)

    return list
