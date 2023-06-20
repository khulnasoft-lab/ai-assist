import os
from pathlib import Path

from typing import Optional, Any, NamedTuple

__all__ = [
    "Config",
    "TritonConfig",
    "FastApiConfig",
    "AuthConfig",
    "PalmTextModelConfig",
    "Project",
    "FeatureFlags",
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
    metrics_host: str
    metrics_port: int
    uvicorn_logger: dict


class AuthConfig(NamedTuple):
    gitlab_base_url: str
    gitlab_api_base_url: str
    bypass: bool


class ProfilingConfig(NamedTuple):
    enabled: bool
    verbose: int
    period_ms: int


class PalmTextModelConfig(NamedTuple):
    names: list[str]
    project: str
    location: str
    vertex_api_endpoint: str
    real_or_fake: str


class GitLabCodegenModelConfig(NamedTuple):
    real_or_fake: str


class Project(NamedTuple):
    id: int
    full_name: str


class FeatureFlags(NamedTuple):
    is_third_party_ai_default: bool
    limited_access_third_party_ai: dict[int, Project]
    third_party_rollout_percentage: int


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
            metrics_host=Config._get_value("FASTAPI_API_METRICS_HOST", "0.0.0.0"),
            metrics_port=int(Config._get_value("FASTAPI_API_METRICS_PORT", 8082)),
            uvicorn_logger=Config.STRUCTURED_LOGGING
        )

    @property
    def auth(self) -> AuthConfig:
        return AuthConfig(
            gitlab_base_url=Config._get_value("GITLAB_URL", "https://gitlab.com/"),
            gitlab_api_base_url=Config._get_value("GITLAB_API_URL", "https://gitlab.com/api/v4/"),
            bypass=Config._str_to_bool(Config._get_value("AUTH_BYPASS_EXTERNAL", "False"))
        )

    @property
    def profiling(self) -> ProfilingConfig:
        return ProfilingConfig(
            enabled=Config._str_to_bool(Config._get_value("GOOGLE_CLOUD_PROFILER", "False")),
            verbose=int(Config._get_value("GOOGLE_CLOUD_PROFILER_VERBOSE", 2)),
            period_ms=int(Config._get_value("GOOGLE_CLOUD_PROFILER_PERIOD_MS", 10)),
        )

    @property
    def feature_flags(self) -> FeatureFlags:
        limited_access = dict()
        if file_path := Config._get_value("F_THIRD_PARTY_AI_LIMITED_ACCESS", ""):
            projects = _read_projects_from_file(Path(file_path))
            limited_access = {project.id: project for project in projects}

        return FeatureFlags(
            is_third_party_ai_default=Config._str_to_bool(Config._get_value("F_IS_THIRD_PARTY_AI_DEFAULT", "False")),
            limited_access_third_party_ai=limited_access,
            third_party_rollout_percentage=int(
                Config._get_value("F_THIRD_PARTY_ROLLOUT_PERCENTAGE", 0)
            ),
        )

    @property
    def palm_text_model(self) -> PalmTextModelConfig:
        names = []
        if s := Config._get_value("PALM_TEXT_MODEL_NAME", "text-bison,code-bison,code-gecko"):
            names = s.split(",")

        return PalmTextModelConfig(
            names=names,
            project=Config._get_value("PALM_TEXT_PROJECT", "unreview-poc-390200e5"),
            location=Config._get_value("PALM_TEXT_LOCATION", "us-central1"),
            vertex_api_endpoint=Config._get_value("VERTEX_API_ENDPOINT", "us-central1-aiplatform.googleapis.com"),
            real_or_fake=Config._parse_fake_models(
                Config._get_value("USE_FAKE_MODELS", "False")
            ),
        )

    @property
    def gitlab_codegen_model(self) -> GitLabCodegenModelConfig:
        return GitLabCodegenModelConfig(
            real_or_fake=Config._parse_fake_models(
                Config._get_value("USE_FAKE_MODELS", "False")
            ),
        )

    @staticmethod
    def _get_value(value: str, default: Optional[Any]):
        return os.environ.get(value, default)

    @staticmethod
    def _str_to_bool(value: str):
        if value.lower() not in Config.BOOLEAN_STATES:
            raise ValueError('Not a boolean: %s' % value)
        return Config.BOOLEAN_STATES[value.lower()]

    @staticmethod
    def _parse_fake_models(value: str) -> str:
        return "fake" if Config._str_to_bool(value) else "real"


def _read_projects_from_file(file_path: Path, sep: str = ",") -> list[Project]:
    projects = []
    with open(str(file_path), "r") as f:
        for line in f.readlines():
            line_split = line.strip().split(sep, maxsplit=2)
            projects.append(Project(
                id=int(line_split[0]),
                full_name=line_split[1],
            ))

    return projects
