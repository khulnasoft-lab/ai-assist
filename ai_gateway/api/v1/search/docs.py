import time
from typing import Annotated

from dependency_injector import providers
from dependency_injector.providers import Factory
from fastapi import APIRouter, Depends, HTTPException, Request, status
from gitlab_cloud_connector import GitLabFeatureCategory, GitLabUnitPrimitive

from ai_gateway.api.auth_utils import StarletteUser, get_current_user
from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v1.search.typing import (
    SearchRequest,
    SearchResponse,
    SearchResponseDetails,
    SearchResponseMetadata,
    SearchResult,
)
from ai_gateway.async_dependency_resolver import (
    get_internal_event_client,
    get_search_factory_provider,
)
from ai_gateway.internal_events import InternalEventsClient
from ai_gateway.searches import Searcher

__all__ = [
    "router",
]

from ai_gateway.structured_logging import get_request_logger

router = APIRouter()

request_log = get_request_logger("search")


def estimate_token_count(text: str) -> int:
    """Estimate the number of tokens in a given text (approx: 1.4 x word count)."""
    return int(len(text.split()) * 1.4)


@router.post(
    "/gitlab-docs", response_model=SearchResponse, status_code=status.HTTP_200_OK
)
@feature_category(GitLabFeatureCategory.DUO_CHAT)
async def docs(
    request: Request,
    current_user: Annotated[StarletteUser, Depends(get_current_user)],
    search_request: SearchRequest,
    search_factory: Factory[Searcher] = Depends(get_search_factory_provider),
    internal_event_client: InternalEventsClient = Depends(get_internal_event_client),
):
    if not current_user.can(GitLabUnitPrimitive.DOCUMENTATION_SEARCH):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to search documentations",
        )

    internal_event_client.track_event(
        f"request_{GitLabUnitPrimitive.DOCUMENTATION_SEARCH}",
        category=__name__,
    )

    payload = search_request.payload

    search_params = {
        "query": payload.query,
        "page_size": payload.page_size,
        "gl_version": search_request.metadata.version,
    }

    searcher = search_factory()

    response = await searcher.search_with_retry(**search_params)
    config = providers.Configuration(strict=True)
    custom_models_enabled = config.custom_models.enabled

    if custom_models_enabled:
        # Apply token limit (8K tokens)
        max_tokens = 8000
        token_count = 0
        filtered_results = []

        for result in response:
            tokens = estimate_token_count(result["content"])
            if token_count + tokens > max_tokens:
                break
            token_count += tokens
            filtered_results.append(
                SearchResult(
                    id=result["id"],
                    content=result["content"],
                    metadata=result["metadata"],
                )
            )

        request_log.info(
            "Search completed with token limiting",
            self_hosted_models_enabled=custom_models_enabled,
            search_params=search_params,
            results_metadata=[res["metadata"] for res in response],
            total_results=len(response),
            total_tokens=token_count,
            max_tokens=max_tokens,
            filtered_results_count=len(filtered_results),
            filtered_results_ids=[res.id for res in filtered_results],
        )

        return SearchResponse(
            response=SearchResponseDetails(
                results=filtered_results,
            ),
            metadata=SearchResponseMetadata(
                provider=searcher.provider(),
                timestamp=int(time.time()),
            ),
        )

    # When custom models is disabled
    results = [
        SearchResult(id=res["id"], content=res["content"], metadata=res["metadata"])
        for res in response
    ]

    request_log.info(
        "Search completed",
        search_params=search_params,
        results_metadata=[res["metadata"] for res in response],
    )

    return SearchResponse(
        response=SearchResponseDetails(
            results=results,
        ),
        metadata=SearchResponseMetadata(
            provider=searcher.provider(),
            timestamp=int(time.time()),
        ),
    )
