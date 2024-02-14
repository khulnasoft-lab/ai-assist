from time import time

import structlog
from dependency_injector.providers import Factory
from fastapi import APIRouter, Depends, Request, status
from starlette.authentication import requires

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v1.search.typing import (
    SearchRequest,
    SearchResponse,
    SearchResponseDetails,
    SearchResponseMetadata,
    SearchResult,
)
from ai_gateway.async_dependency_resolver import get_vertex_search_factory_provider
from ai_gateway.searches.container import VertexAISearch

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("search")

router = APIRouter()


@router.post("/docs", response_model=SearchResponse, status_code=status.HTTP_200_OK)
@requires("duo_chat")
@feature_category("duo_chat")
async def docs(
    request: Request,
    search_request: SearchRequest,
    vertex_search_factory: Factory[VertexAISearch] = Depends(
        get_vertex_search_factory_provider
    ),
):
    print(f"search_request: {search_request}")
    payload = search_request.payload

    search_params = {"query": payload.query, "gl_version": search_request.metadata.version}
    if payload.params:
        search_params.update(payload.params.dict())

    searcher = vertex_search_factory()

    response = searcher.search(**search_params)

    results = []
    if "results" in response:
        for r in response["results"]:
            search_result = SearchResult(
                id=r["document"]["id"],
                content=r["document"]["structData"]["content"],
                metadata=r["document"]["structData"]["metadata"],
            )
            results.append(search_result)

    return SearchResponse(
        response=SearchResponseDetails(
            results=results,
        ),
        metadata=SearchResponseMetadata(
            provider="vertex-ai",
            timestamp=int(time()),
        ),
    )
