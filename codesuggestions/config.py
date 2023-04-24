import os

from typing import Optional, Any, NamedTuple

__all__ = [
    "Config",
    "TritonConfig",
    "FastApiConfig",
    "AuthConfig",
]


class TritonConfig(NamedTuple):
    host: str
    port: int


class FastApiConfig(NamedTuple):
    docs_url: str
    openapi_url: str
    redoc_url: str
    api_host: str
    api_port: int
    uvicorn_logger: dict


class AuthConfig(NamedTuple):
    gitlab_api_base_url: str
    bypass: bool


class PalmTextModelConfig(NamedTuple):
    api_endpoint: str
    project: str
    location: str
    endpoint_id: str

class Config:
    BOOLEAN_STATES = {
        '1': True, 'yes': True, 'true': True, 'on': True,
        '0': False, 'no': False, 'false': False, 'off': False
    }

    STRUCTURED_LOGGING = {
        "version": 1,
        "disable_existing_loggers": False
    }

    @property
    def triton(self) -> TritonConfig:
        return TritonConfig(
            host=Config._get_value("TRITON_HOST", "triton"),
            port=int(Config._get_value("TRITON_PORT", 8001)),
        )

    @property
    def fastapi(self) -> FastApiConfig:
        return FastApiConfig(
            docs_url=Config._get_value("FASTAPI_DOCS_URL", None),
            openapi_url=Config._get_value("FASTAPI_OPENAPI_URL", None),
            redoc_url=Config._get_value("FASTAPI_REDOC_URL", None),
            api_host=Config._get_value("FASTAPI_API_HOST", "0.0.0.0"),
            api_port=int(Config._get_value("FASTAPI_API_PORT", 5000)),
            uvicorn_logger=Config.STRUCTURED_LOGGING
        )

    @property
    def auth(self) -> AuthConfig:
        return AuthConfig(
            gitlab_api_base_url=Config._get_value("GITLAB_API_URL", "https://gitlab.com/api/v4/"),
            bypass=Config._str_to_bool(Config._get_value("AUTH_BYPASS_EXTERNAL", "False"))
        )

    @property
    def is_generative_ai_only(self) -> bool:
        return Config._str_to_bool(Config._get_value("GENERATIVE_AI_ONLY", "False"))

    @property
    def palm_text_model(self) -> PalmTextModelConfig:
        return PalmTextModelConfig(
            api_endpoint=Config._get_value("PALM_TEXT_API_ENDPOINT", "us-central1-aiplatform.googleapis.com"),
            project=Config._get_value("PALM_TEXT_PROJECT", "cloud-large-language-models"),
            location=Config._get_value("PALM_TEXT_LOCATION", "us-central1"),
            endpoint_id=Config._get_value("PALM_TEXT_ENDPOINT_ID", "4511608470067216384"),
        )

    @staticmethod
    def _get_value(value: str, default: Optional[Any]):
        return os.environ.get(value, default)

    @staticmethod
    def _str_to_bool(value: str):
        if value.lower() not in Config.BOOLEAN_STATES:
            raise ValueError('Not a boolean: %s' % value)
        return Config.BOOLEAN_STATES[value.lower()]
