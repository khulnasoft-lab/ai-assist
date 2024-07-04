import functools
import typing

from fastapi import HTTPException, Request, status
from gitlab_cloud_connector.models import FeatureCategory, UnitPrimitive
from starlette_context import context

X_GITLAB_UNIT_PRIMITIVE = "x-gitlab-unit-primitive"

_CATEGORY_CONTEXT_KEY = "meta.feature_category"
_UNIT_PRIMITIVE_CONTEXT_KEY = "meta.unit_primitive"
_UNKNOWN_FEATURE_CATEGORY = "unknown"


def feature_category(name: FeatureCategory):
    """
    Track a feature category in a single purpose endpoint.

    Example:

    ```
    @feature_category(FeatureCategory.DUO_CHAT)
    ```
    """
    try:
        FeatureCategory(name)
    except ValueError:
        raise ValueError(f"Invalid feature category: {name}")

    def decorator(func: typing.Callable) -> typing.Callable:
        @functools.wraps(func)
        async def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
            context[_CATEGORY_CONTEXT_KEY] = name
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def feature_categories(mapping: dict[UnitPrimitive, FeatureCategory]):
    """
    Track feature categories in a multi purpose endpoint.

    It gets the purpose of API call from X-GitLab-Unit-Primitive header,
    identifies the corresponding feature category and stores them in the Starlette context.

    Example:

    ```
    @feature_category({
        UnitPrimitive.EXPLAIN_VULNERABILITY: FeatureCategory.VULNERABILITY_MANAGEMENT,
        UnitPrimitive.GENERATE_COMMIT_MESSAGE: FeatureCategory.CODE_REVIEW_WORKFLOW,
    }
    ```
    """
    for category in mapping.values():
        try:
            FeatureCategory(category)
        except ValueError:
            raise ValueError(f"Invalid feature category: {category}")

    def decorator(func: typing.Callable) -> typing.Callable:
        @functools.wraps(func)
        async def wrapper(
            request: Request, *args: typing.Any, **kwargs: typing.Any
        ) -> typing.Any:
            try:
                unit_primitive = request.headers[X_GITLAB_UNIT_PRIMITIVE]
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing {X_GITLAB_UNIT_PRIMITIVE} header",
                )

            try:
                feature_category = mapping[unit_primitive]
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"This endpoint cannot be used for {unit_primitive} purpose",
                )

            context[_CATEGORY_CONTEXT_KEY] = feature_category
            context[_UNIT_PRIMITIVE_CONTEXT_KEY] = unit_primitive
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def current_feature_category() -> str:
    """
    Get the feature category set to the current request context.
    """
    if context.exists():
        feature_category = context.get(_CATEGORY_CONTEXT_KEY, _UNKNOWN_FEATURE_CATEGORY)

        if isinstance(feature_category, FeatureCategory):
            return feature_category.value

        return feature_category

    return _UNKNOWN_FEATURE_CATEGORY
