from dependency_injector.wiring import Provide, inject
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette_context.middleware import RawContextMiddleware

from ai_gateway.api.experimental.code_metadata import create_router
from ai_gateway.api.middleware import (
    MiddlewareAuthentication,
    MiddlewareLogRequest,
    MiddlewareModelTelemetry,
)
from ai_gateway.api.monitoring import router as http_monitoring_router
from ai_gateway.api.v1 import api_router as http_api_router_v1
from ai_gateway.api.v2 import api_router as http_api_router_v2
from ai_gateway.deps import FastApiContainer

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
    telemetry_middleware: MiddlewareModelTelemetry = Provide[
        FastApiContainer.telemetry_middleware
    ],
):
    context_middleware = Middleware(RawContextMiddleware)
    cors_middleware = Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST"],
        allow_headers=["*"],
    )

    fastapi_app = FastAPI(
        title="GitLab Code Suggestions",
        description="GitLab Code Suggestions API to serve code completion predictions",
        openapi_url=config["openapi_url"],
        docs_url=config["docs_url"],
        redoc_url=config["redoc_url"],
        swagger_ui_parameters={"defaultModelsExpandDepth": -1},
        middleware=[
            context_middleware,
            cors_middleware,
            log_middleware,
            auth_middleware,
            telemetry_middleware,
        ],
    )

    fastapi_app.include_router(http_api_router_v1)
    fastapi_app.include_router(http_api_router_v2)
    fastapi_app.include_router(http_monitoring_router)
    fastapi_app.include_router(create_router(), prefix="/experimental")

    return fastapi_app
