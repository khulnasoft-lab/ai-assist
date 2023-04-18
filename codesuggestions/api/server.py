from fastapi import FastAPI
from dependency_injector.wiring import Provide, inject

from codesuggestions.api.suggestions import router as http_suggestions_router
from codesuggestions.api.monitoring import router as http_monitoring_router
from codesuggestions.api.middleware import (
    MiddlewareAuthentication,
    MiddlewareLogRequest,
)
from codesuggestions.api.v2 import APIRouterBuilderV2
from codesuggestions.deps import FastApiContainer

__all__ = [
    "create_code_suggestions_api_server",
    "create_generative_ai_api_server",
]


@inject
def create_code_suggestions_api_server(
    config: dict = Provide[FastApiContainer.config.fastapi],
    auth_middleware: MiddlewareAuthentication = Provide[
        FastApiContainer.auth_middleware
    ],
    log_middleware: MiddlewareLogRequest = Provide[FastApiContainer.log_middleware],
):
    fastapi_app = FastAPI(
        title="GitLab Code Suggestions",
        description="GitLab Code Suggestions API to serve code completion predictions",
        openapi_url=config["openapi_url"],
        docs_url=config["docs_url"],
        redoc_url=config["redoc_url"],
        swagger_ui_parameters={"defaultModelsExpandDepth": -1},
        middleware=[
            log_middleware,
            auth_middleware,
        ],
    )

    fastapi_app.include_router(http_suggestions_router, prefix="/v1")
    fastapi_app.include_router(http_monitoring_router)

    api_router_v2 = (
        APIRouterBuilderV2()
        .with_gl_code_suggestions()
        .router
    )
    fastapi_app.include_router(api_router_v2)

    return fastapi_app


@inject
def create_generative_ai_api_server(
    config: dict = Provide[FastApiContainer.config.fastapi],
):
    fastapi_app = FastAPI(
        title="GitLab AI API",
        description="GitLab AI API to experiment with generative models",
        openapi_url=config["openapi_url"],
        docs_url=config["docs_url"],
        redoc_url=config["redoc_url"],
        swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    )

    api_router_v2 = (
        APIRouterBuilderV2()
        .with_generative_ai()
        .router
    )
    fastapi_app.include_router(api_router_v2)

    return fastapi_app
