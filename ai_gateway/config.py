import os
from typing import Annotated, Optional

from dotenv import find_dotenv
from pydantic import AliasChoices, BaseModel, Field, RootModel
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "Config",
    "ConfigLogging",
    "ConfigFastApi",
    "ConfigAuth",
    "ConfigGoogleCloudProfiler",
    "FFlags",
    "FFlagsCodeSuggestions",
    "ConfigSnowplow",
    "ConfigInstrumentator",
    "ConfigVertexTextModel",
    "ConfigModelConcurrency",
]

ENV_PREFIX = "AIGW"


class ConfigLogging(BaseModel):
    level: str = "INFO"
    format_json: bool = True
    to_file: Optional[str] = None


class ConfigFastApi(BaseModel):
    api_host: str = "0.0.0.0"
    api_port: int = 5000
    metrics_host: str = "0.0.0.0"
    metrics_port: int = 8082
    uvicorn_logger: dict = {"version": 1, "disable_existing_loggers": False}
    docs_url: Optional[str] = None
    openapi_url: Optional[str] = None
    redoc_url: Optional[str] = None
    reload: bool = False


class ConfigAuth(BaseModel):
    bypass_external: bool = False


class ConfigGoogleCloudProfiler(BaseModel):
    enabled: bool = False
    verbose: int = 2
    period_ms: int = 10


class ConfigInstrumentator(BaseModel):
    thread_monitoring_enabled: bool = False
    thread_monitoring_interval: int = 60


class FFlagsCodeSuggestions(BaseModel):
    excl_post_proc: list[str] = []


class FFlags(BaseSettings):
    code_suggestions: Annotated[
        FFlagsCodeSuggestions, Field(default_factory=FFlagsCodeSuggestions)
    ] = FFlagsCodeSuggestions()


class ConfigSnowplow(BaseModel):
    enabled: bool = False
    endpoint: Optional[str] = None
    batch_size: Optional[int] = 10
    thread_count: Optional[int] = 1


def _build_location(default: str = "us-central1") -> str:
    """
    Reads the GCP region from the environment.
    Returns the default argument when not configured.
    """
    return os.getenv("RUNWAY_REGION", default)


def _build_endpoint() -> str:
    """
    Returns the default endpoint for Vertex AI.

    This code assumes that the Runway region (i.e. Cloud Run region) is the same as the Vertex AI region.
    To support other Cloud Run regions, this code will need to be updated to map to a nearby Vertex AI region instead.
    """
    return f"{_build_location()}-aiplatform.googleapis.com"


class ConfigVertexTextModel(BaseModel):
    project: str = "unreview-poc-390200e5"
    location: str = Field(default_factory=_build_location)
    endpoint: str = Field(default_factory=_build_endpoint)
    json_key: str = ""


class ConfigModelConcurrency(RootModel):
    root: dict[str, dict[str, int]] = {}

    def for_model(self, engine: str, name: str) -> Optional[int]:
        return self.root.get(engine, {}).get(name, None)


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_prefix=f"{ENV_PREFIX}_",
        protected_namespaces=(),
        env_file=find_dotenv(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gitlab_url: str = "https://gitlab.com"
    gitlab_api_url: str = "https://gitlab.com/api/v4/"
    customer_portal_url: str = "https://customers.gitlab.com"
    ai_gateway_url: str = "https://codesuggestions.gitlab.com"

    jwt_private_key: str = """
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCAzC66XB4Fppc0
QFmrujl0AnGA7ffgnXvVJTdswIlDrYH/2R5F05ekS0Fzn/tFksyx4RZuakQu4SiP
K0FXipmpkF48wGbkSHLQObTdYmL0A6kF9VWVd29N2hun+gJNnvL32TPG6CEepIvH
UIgkfvvGQCSnFJW8QR+3+U29JsNYRUPsZRKvgV/z1zQt6ZLeBUg1sm5xA7qLsmjH
mThfJCosnmdKoYvZbapmQGhpXcjtmlCSVeibVcosXsnrAiXn7Cs+9caWNvKZMnlT
lY+kZwliOqI/BusFVUIr2/sWi/MsN0UIrtWsqlTlL/JVwqsg6bwANqOFMByZxIRk
GgTCyFO3AgMBAAECggEAAtJ2g6bZEY6g6Ygvbs/ZymzzR7vvHoDU4cq6+CsP1ufK
XWzIeQc132e2u23Z96BL0+n2r9ysOcq9NMXh3KUw0MJVDke4+W+M9HsPN3qcaHRc
E8FYarn/Oll5Gakku8ar1DpyI/2aHC3G0ks1cHdH1QQ6yV5uGX3j0AgqZ+adiSWT
LfbXepCedQp+w29AgnaKBfFb2tVl/5DgCBsR2GDeveFwgmDEZiuS+Mz44XYpLkaF
FWXKfwA+HjOSI+8qUgSdGj/AGvK3E4YZZHqJ8eXLXXHPxL+UQFEgfST1zJQFF51B
X1CfrG5lAgrxra32vsuj36T5uFaXUhdUcSJddQJsoQKBgQDpUGixsX1Lynn6JzwQ
1MT/CvVxMF57Af2xFeggfwpiTCa8eKw/vjxXcFoQIbnTSr+ugGuyPEHwmImLR0Qj
FQE4kbM7vwuRKtJVCkqppeBA4xAmA3qwW5/YLoVO1Qp4dqPWSaczQJeNM8+4+Z5C
tD88NPOjzkTTlpNxw84nnI1FrQKBgQCNUi1TMVdUCz6ZPINyCtjNAMam7yEtiegh
xRr/A/v83ku+Gy3ZfOQbRcarRxkmDHHsPwpSCnHHUIBTaFKlMqmAEl3u58fmYVSR
pJSgvxuYJGS+GAJsmQ/VQvaYA9sH93mV3VZBQOtNrRsalfdoSgMo7KArsSisArgb
0ElDO6UDcwKBgFmVsl1oVT/gwu02W23rBKkZQBzyAZUhspNoYfT4UrhjnQwJGbpw
BSNd1HcVPBDRRsBuNuv9DySerVF5T8RYsFtUNoneVUasNo7IoNp7Apxnky/FbjqB
M+MCGdWnH5oZk9cX+MdJKefh2QShdA8QvqcTfemLrgnAa2TnViUHi4cRAoGAcgyx
24PkcEUq3cwCYNT0Jm3L5Aj0g6XaGvbRVKFIich05BVXKUArbv8e2Ddmylgc0IYH
tDINpMcI6Uc1+3Apbtxjxlxz7S77axahhCD3Cg/E5czGmBHmvzttez0RVRqZmyKn
a74Sp/td9lS0+AtTBYIBuYEdy8PeBURQ+9t0zpUCgYEAhefNoiILN3OO+fgv/L+7
meZ76Z9wPG3CuNPtQqgG4zHy57z9bZMcDMHnL60NV6liH0E8CxGQ07NGjI3qdfs9
/Osy0rv4v39yWpNt4M6d7lqyZoIydfrhU0RQqCtRUoZuql73R0KpD89r9uiaLaxd
cmOY8Rcamyo/giOO9+jYMaU=
-----END PRIVATE KEY-----
"""

    mock_model_responses: bool = Field(
        validation_alias=AliasChoices(
            f"{ENV_PREFIX.lower()}_mock_model_responses",
            f"{ENV_PREFIX.lower()}_use_fake_models",  # Backward compatibility with the GitLab QA tests
        ),
        default=False,
    )

    logging: Annotated[ConfigLogging, Field(default_factory=ConfigLogging)] = (
        ConfigLogging()
    )
    fastapi: Annotated[ConfigFastApi, Field(default_factory=ConfigFastApi)] = (
        ConfigFastApi()
    )
    auth: Annotated[ConfigAuth, Field(default_factory=ConfigAuth)] = ConfigAuth()
    google_cloud_profiler: Annotated[
        ConfigGoogleCloudProfiler, Field(default_factory=ConfigGoogleCloudProfiler)
    ] = ConfigGoogleCloudProfiler()
    instrumentator: Annotated[
        ConfigInstrumentator, Field(default_factory=ConfigInstrumentator)
    ] = ConfigInstrumentator()
    f: Annotated[FFlags, Field(default_factory=FFlags)] = FFlags()
    snowplow: Annotated[ConfigSnowplow, Field(default_factory=ConfigSnowplow)] = (
        ConfigSnowplow()
    )
    vertex_text_model: Annotated[
        ConfigVertexTextModel, Field(default_factory=ConfigVertexTextModel)
    ] = ConfigVertexTextModel()
    model_engine_concurrency_limits: Annotated[
        ConfigModelConcurrency, Field(default_factory=ConfigModelConcurrency)
    ] = ConfigModelConcurrency()
