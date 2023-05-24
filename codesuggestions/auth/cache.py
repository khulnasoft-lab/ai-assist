from collections import OrderedDict
from datetime import datetime
from typing import Optional, NamedTuple
from abc import ABC, abstractmethod
from prometheus_client import Gauge

__all__ = [
    "AuthRecord",
    "BaseAuthCache",
    "LocalAuthCache",
]

LOCAL_AUTH_CACHE_KEY_GAUGE = Gauge('local_auth_cache_count', 'Number of keys in local auth cache', ['name'])


class AuthRecord(NamedTuple):
    value: str
    exp: datetime


class BaseAuthCache(ABC):
    def __init__(self, expiry_seconds: int = 3600):
        self.expiry_seconds = expiry_seconds

    @abstractmethod
    def set(self, k: str, val: str, exp: datetime):
        pass

    @abstractmethod
    def get(self, k: str) -> Optional[AuthRecord]:
        pass

    @abstractmethod
    def delete(self, k: str):
        pass


class LocalAuthCache(BaseAuthCache):
    def __init__(self, name: str, capacity: int):
        super().__init__()
        self.capacity = capacity
        self.in_memory_cache = OrderedDict()
        self.name = name

    def set(self, k: str, val: str, exp: datetime):
        self.in_memory_cache[k] = AuthRecord(
            value=val,
            exp=exp,
        )
        self.in_memory_cache.move_to_end(k)

        if len(self.in_memory_cache) > self.capacity:
            self.in_memory_cache.popitem(last=False)

        LOCAL_AUTH_CACHE_KEY_GAUGE.labels(name=self.name).set(len(self.in_memory_cache))

    def get(self, k: str) -> Optional[AuthRecord]:
        record = self.in_memory_cache.get(k, None)
        if record is None:
            return None

        self.in_memory_cache.move_to_end(k)
        return record

    def delete(self, k: str):
        self.in_memory_cache.pop(k, None)
