from logging.config import dictConfig

from dotenv import load_dotenv

from ai_gateway.api import create_fast_api_server
from ai_gateway.config import Config
from fastapi.exception_handlers import http_exception_handler
from prometheus_client import start_http_server
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette_context import context

from ai_gateway.api import create_fast_api_server
from ai_gateway.config import Config
from ai_gateway.instrumentators.threads import monitor_threads
from ai_gateway.profiling import setup_profiling
from ai_gateway.structured_logging import setup_logging

# load env variables from .env if exists
load_dotenv()

# prepare configuration settings
config = Config()

# configure logging
dictConfig(config.fastapi.uvicorn_logger)


def get_config():
    return config


def get_app():
    app = create_fast_api_server(config)
    return app
