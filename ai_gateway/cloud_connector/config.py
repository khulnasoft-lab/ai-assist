import os


class CloudConnectorConfig:
    DEFAULT_SERVICE_NAME = "gitlab-ai-gateway"

    # pylint: disable=direct-environment-variable-reference
    @property
    def service_name(self) -> str:
        return os.environ.get("CLOUD_CONNECTOR_SERVICE_NAME", self.DEFAULT_SERVICE_NAME)

    # pylint: enable=direct-environment-variable-reference
