from datetime import datetime
from typing import Optional, NamedTuple
from abc import ABC, abstractmethod
from fastapi.encoders import jsonable_encoder

import json
import redis

__all__ = [
    "AuthRecord",
    "BaseAuthCache",
    "LocalAuthCache",
]


class AuthRecord(NamedTuple):
    value: str
    exp: datetime

    def to_json(self):
        return json.dumps(self, default=jsonable_encoder)

    @classmethod
    def from_json(data):
        payload = json.loads(data)
        return AuthRecord(value=payload['value'], exp=datetime.fromisoformat(payload['exp']))


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
    def __init__(self):
        super().__init__()
        self.in_memory_cache = dict()

    def set(self, k: str, val: str, exp: datetime):
        self.in_memory_cache[k] = AuthRecord(
            value=val,
            exp=exp,
        )

    def get(self, k: str) -> Optional[AuthRecord]:
        record = self.in_memory_cache.get(k, None)
        if record is None:
            return None
        return record

    def delete(self, k: str):
        self.in_memory_cache.pop(k, None)


class RedisAuthCache(BaseAuthCache):
    def __init__(self, url):
        super().__init__()
        self.redis = redis.Redis.from_url(url)

    def set(self, k: str, val: str, exp: datetime):
        json_data = AuthRecord(value=val, exp=exp).to_json()
        self.redis.set(name=k, value=json_data)

    def get(self, k: str) -> Optional[AuthRecord]:
        data = self.redis.get(k)

        if data is None:
            return None

        try:
            return AuthRecord.from_json(data)
        except TypeError:
            return None

    def delete(self, k: str):
        self.redis.expire(k)
