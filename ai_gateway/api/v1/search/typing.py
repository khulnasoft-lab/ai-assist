from typing import Annotated, List, Optional

from pydantic import BaseModel, StringConstraints

__all__ = [
    "SearchRequest",
    "SearchResponseMetadata",
    "SearchResponse",
]


class SearchMetadata(BaseModel):
    source: Annotated[str, StringConstraints(max_length=100)]
    version: Annotated[str, StringConstraints(max_length=100)]


class SearchParams(BaseModel):
    page_size: int = 10
    filter: str = ""


class SearchPayload(BaseModel):
    query: Annotated[str, StringConstraints(max_length=400000)]
    params: Optional[SearchParams]


class SearchRequest(BaseModel):
    type: Annotated[str, StringConstraints(max_length=100)]
    metadata: SearchMetadata
    payload: SearchPayload


class SearchResponseMetadata(BaseModel):
    provider: str


class SearchResult(BaseModel):
    id: str
    content: str
    metadata: dict


class SearchResponseDetails(BaseModel):
    results: List[SearchResult]


class SearchResponse(BaseModel):
    response: SearchResponseDetails
    metadata: SearchResponseMetadata
