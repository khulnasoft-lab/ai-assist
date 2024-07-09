import pdb

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from ai_gateway.api.feature_category import feature_category
from ai_gateway.gitlab_features import GitLabFeatureCategory

__all__ = [
    "router",
]

class Blob(BaseModel):
    language: str
    content: str
    line: int

log = structlog.stdlib.get_logger("codesuggestions")

router = APIRouter()


@router.post("/chunk")
@feature_category(GitLabFeatureCategory.CODE_SUGGESTIONS)
async def chunk(blob: Blob):
    language = blob.language
    content = blob.content
    line = blob.line
    # at the moment this just returns a subset of the blob
    # we want to use tree-sitter to do this instead
    num_lines = 2
    lines = content.splitlines()
    start = max(0, line - (num_lines + 1))
    end = min(len(lines), line + num_lines)
    chunk = "\n".join(lines[start:end])

    return chunk
