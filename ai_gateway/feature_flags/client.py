from contextvars import ContextVar

from UnleashClient import UnleashClient

__all__ = ["is_enabled", "init_feature_flag_client"]

def lookup_local_definitions(feature_name: str, context: dict) -> bool:
    # TODO:
    return True

def is_enabled(feature_name: str) -> bool:
    client: UnleashClient = unleash_client.get()
    return client.is_enabled(feature_name, fallback_function=lookup_local_definitions)


def init_feature_flag_client(enabled: bool, url: str, app_name: str, instance_id: str):
    """Initialize the feature flag client"""
    client = UnleashClient(url=url, app_name=app_name, instance_id=instance_id)

    client.initialize_client()

    unleash_client.set(client)


unleash_client: ContextVar[UnleashClient] = ContextVar("unleash_client")
