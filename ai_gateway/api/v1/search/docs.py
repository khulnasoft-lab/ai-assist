import time
from typing import Annotated

import structlog
from dependency_injector.providers import Factory
from fastapi import APIRouter, Depends, HTTPException, Request, status
from gitlab_cloud_connector import FeatureCategory, UnitPrimitive

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v1.search.typing import (
    SearchRequest,
    SearchResponse,
    SearchResponseDetails,
    SearchResponseMetadata,
    SearchResult,
)
from ai_gateway.async_dependency_resolver import get_search_factory_provider
from ai_gateway.auth.user import GitLabUser, get_current_user
from ai_gateway.searches import Searcher

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("search")

router = APIRouter()


@router.post(
    "/gitlab-docs", response_model=SearchResponse, status_code=status.HTTP_200_OK
)
@feature_category(FeatureCategory.DUO_CHAT)
async def docs(
    request: Request,
    current_user: Annotated[GitLabUser, Depends(get_current_user)],
    search_request: SearchRequest,
    search_factory: Factory[Searcher] = Depends(get_search_factory_provider),
):
    if not current_user.can(UnitPrimitive.DOCUMENTATION_SEARCH):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to search documentations",
        )

    payload = search_request.payload

    search_params = {
        "query": payload.query,
        "page_size": payload.page_size,
        "gl_version": search_request.metadata.version,
    }

    searcher = search_factory()

    response = await searcher.search_with_retry(**search_params)

    results = [
        SearchResult(
            id=result["id"], content=result["content"], metadata=result["metadata"]
        )
        for result in response
    ]

    return SearchResponse(
        response=SearchResponseDetails(
            results=results,
        ),
        metadata=SearchResponseMetadata(
            provider=searcher.provider(),
            timestamp=int(time.time()),
        ),
    )
