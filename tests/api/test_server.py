import asyncio
import os
import socket
from typing import Iterator, cast
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from ai_gateway.api import create_fast_api_server, server
from ai_gateway.config import Config, ConfigAuth
from ai_gateway.container import ContainerApplication

_ROUTES_V1 = [
    ("/v1/chat/agent", ["POST"]),
    ("/v1/x-ray/libraries", ["POST"]),
]

_ROUTES_V2 = [
    ("/v2/code/completions", ["POST"]),
    ("/v2/completions", ["POST"]),  # legacy path
    ("/v2/code/generations", ["POST"]),
]

_ROUTES_V3 = [
    ("/v3/code/completions", ["POST"]),
]


@pytest.fixture(scope="module")
def unused_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return port


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def app():
    return FastAPI()


@pytest.fixture
def container_application():
    container_app = ContainerApplication()
    container_app.init_resources = MagicMock()
    container_app.shutdown_resources = MagicMock()
    return container_app


@pytest.fixture(scope="session")
def auth_enabled():
    return os.environ.get("AIGW_AUTH__BYPASS_EXTERNAL", "False") == "False"


@pytest.fixture(scope="session")
def fastapi_server_app(auth_enabled) -> Iterator[FastAPI]:
    config = Config(_env_file=None, auth=ConfigAuth(bypass_external=not auth_enabled))
    fast_api_container = ContainerApplication()
    fast_api_container.config.from_dict(config.model_dump())
    yield create_fast_api_server(config)


@pytest.mark.parametrize("routes_expected", [_ROUTES_V1, _ROUTES_V2, _ROUTES_V3])
class TestServerRoutes:
    def test_routes_available(
        self,
        fastapi_server_app: FastAPI,
        routes_expected: list,
    ):
        routes_expected = [
            (path, method) for path, methods in routes_expected for method in methods
        ]

        routes_actual = [
            (cast(APIRoute, route).path, method)
            for route in fastapi_server_app.routes
            for method in cast(APIRoute, route).methods
        ]

        assert set(routes_expected).issubset(routes_actual)

    def test_routes_reachable(
        self,
        fastapi_server_app: FastAPI,
        auth_enabled: bool,
        routes_expected: list,
    ):
        client = TestClient(fastapi_server_app)

        routes_expected = [
            (path, method) for path, methods in routes_expected for method in methods
        ]

        for path, method in routes_expected:
            res = client.request(method, path)
            if auth_enabled:
                assert res.status_code == 401
            else:
                if method == "POST":
                    # We're checking the route availability only
                    assert res.status_code == 422
                else:
                    assert False


def test_setup_router():
    app = FastAPI()
    server.setup_router(app)

    assert any(route.path == "/v1/chat/agent" for route in app.routes)
    assert any(route.path == "/v2/code/completions" for route in app.routes)
    assert any(route.path == "/v3/code/completions" for route in app.routes)
    assert any(route.path == "/monitoring/healthz" for route in app.routes)


def test_setup_prometheus_fastapi_instrumentator():
    app = FastAPI()
    server.setup_prometheus_fastapi_instrumentator(app)

    assert any(
        "Prometheus" in middleware.cls.__name__ for middleware in app.user_middleware
    )


@pytest.mark.asyncio
async def test_lifespan(config, app, unused_port, monkeypatch):
    mock_credentials = MagicMock()
    mock_credentials.client_id = "mocked_client_id"

    def mock_default(*args, **kwargs):
        return (mock_credentials, "mocked_project_id")

    monkeypatch.setattr("google.auth.default", mock_default)

    mock_container_app = MagicMock(spec=ContainerApplication)
    monkeypatch.setattr(
        "ai_gateway.api.server.ContainerApplication", mock_container_app
    )
    monkeypatch.setattr(asyncio, "get_running_loop", MagicMock())

    config.fastapi.metrics_port = unused_port

    async with server.lifespan(app, config):
        mock_container_app.assert_called_once()
        assert mock_container_app.return_value.config.from_dict.called_once_with(
            config.model_dump()
        )
        assert mock_container_app.return_value.init_resources.called_once()

        if config.instrumentator.thread_monitoring_enabled:
            asyncio.get_running_loop.assert_called_once()

    assert mock_container_app.return_value.shutdown_resources.called_once()


def test_middleware_authentication(fastapi_server_app: FastAPI, auth_enabled: bool):
    client = TestClient(fastapi_server_app)

    response = client.post("/v1/chat/agent")
    if auth_enabled:
        assert response.status_code == 401
    else:
        assert response.status_code == 422

    response = client.get("/monitoring/healthz")
    assert response.status_code == 200


def test_middleware_log_request(fastapi_server_app: FastAPI, caplog):
    client = TestClient(fastapi_server_app)

    with caplog.at_level("INFO"):
        client.post("/v1/chat/agent")
        log_messages = [record.message for record in caplog.records]
        assert any("HTTP Request" in msg for msg in log_messages)

    with caplog.at_level("INFO"):
        client.get("/metrics")
        log_messages = [record.message for record in caplog.records]
        assert all("HTTP Request" not in msg for msg in log_messages)
