from dependency_injector.wiring import Provide, inject
from fastapi import FastAPI
from starlette.middleware import Middleware
from starlette_context.middleware import RawContextMiddleware

from codesuggestions.api.middleware import (
    MiddlewareAuthentication,
    MiddlewareLogRequest,
)
from codesuggestions.api.monitoring import router as http_monitoring_router
from codesuggestions.api.suggestions import router as http_suggestions_router
from codesuggestions.api.v2.api import api_router as api_router_v2
from codesuggestions.deps import FastApiContainer

__all__ = [
    "create_fast_api_server",
]


@inject
def create_fast_api_server(
    config: dict = Provide[FastApiContainer.config.fastapi],
    auth_middleware: MiddlewareAuthentication = Provide[
        FastApiContainer.auth_middleware
    ],
    log_middleware: MiddlewareLogRequest = Provide[FastApiContainer.log_middleware],
):

    context_middleware = Middleware(RawContextMiddleware)

    fastapi_app = FastAPI(
        title="GitLab Code Suggestions",
        description="GitLab Code Suggestions API to serve code completion predictions",
        openapi_url=config["openapi_url"],
        docs_url=config["docs_url"],
        redoc_url=config["redoc_url"],
        swagger_ui_parameters={"defaultModelsExpandDepth": -1},
        middleware=[
            context_middleware,
            log_middleware,
            auth_middleware,
        ],
    )

    fastapi_app.include_router(http_suggestions_router, prefix="/v1")
    fastapi_app.include_router(api_router_v2)
    fastapi_app.include_router(http_monitoring_router)

    return fastapi_app
