from codesuggestions.auth.cache import LocalAuthCache
from datetime import datetime


def test_local_auth_cache():
    cache = LocalAuthCache(name='test-cache', capacity=2)
    current = datetime.now()

    cache.set(k="key1", val="value1", exp=current)
    assert cache.get("key1").value == "value1"

    cache.set(k="key2", val="value2", exp=current)
    assert cache.get("key1").value == "value1"
    assert cache.get("key2").value == "value2"

    cache.set(k="key3", val="value3", exp=current)
    assert cache.get("key2").value == "value2"
    assert cache.get("key3").value == "value3"
    assert cache.get("key1") is None
