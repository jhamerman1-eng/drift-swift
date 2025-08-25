import os

try:
    import redis  # type: ignore
except Exception:
    redis = None

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

_client = None

def _get_client():
    global _client
    if _client is None and redis is not None:
        _client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD)
    return _client

FLAG_KEYS = {
    "obi_enabled": "feature:obi:enabled",
    "trend_enabled": "feature:trend:enabled",
    "hedge_enabled": "feature:hedge:enabled",
}

def get_flag(name: str, fallback: bool) -> bool:
    """Read feature flag from Redis; fallback to local default."""
    key = FLAG_KEYS.get(name, name)
    c = _get_client()
    if c is None:
        return fallback
    try:
        v = c.get(key)
        if v is None:
            return fallback
        return v.decode().lower() in ("1", "true", "yes", "on")
    except Exception:
        return fallback
