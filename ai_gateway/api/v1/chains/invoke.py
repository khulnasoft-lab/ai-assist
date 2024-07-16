from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import RootModel

from ai_gateway.api.feature_category import feature_category
from ai_gateway.async_dependency_resolver import get_container_application
from ai_gateway.auth.user import GitLabUser, get_current_user
from ai_gateway.chains import BaseChainRegistry, Chain
from ai_gateway.gitlab_features import GitLabFeatureCategory, WrongUnitPrimitives


class ChainRequest(RootModel):
    root: dict[str, Any]


router = APIRouter()


async def get_chain_registry():
    yield get_container_application().chains.chain_registry()


@router.post(
    "/{chain_id:path}",
    response_model=str,
    status_code=status.HTTP_200_OK,
)
@feature_category(GitLabFeatureCategory.AI_ABSTRACTION_LAYER)
async def chain(
    request: Request,
    chain_request: ChainRequest,
    chain_id: str,
    current_user: Annotated[GitLabUser, Depends(get_current_user)],
    chain_registry: Annotated[BaseChainRegistry, Depends(get_chain_registry)],
):
    try:
        chain = chain_registry.get_on_behalf(current_user, chain_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chain '{chain_id}' not found",
        )
    except WrongUnitPrimitives:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized to access '{chain_id}'",
        )

    # We don't use `isinstance` because we don't want to match subclasses
    if not type(chain) is Chain:  # pylint: disable=unidiomatic-typecheck
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Chain '{chain_id}' is not supported",
        )

    try:
        response = await chain.ainvoke(chain_request.root)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return response.content
