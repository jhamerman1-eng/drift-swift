import aiohttp, asyncio, time
from .errors import RetryExhausted
from .utils.backoff import sleep_backoff

class RateLimiter:
    """Simple token-bucket rate limiter for asyncio."""
    def __init__(self, qps: int, burst: int):
        self.capacity = max(burst, qps)
        self.tokens = self.capacity
        self.qps = qps
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.updated
            self.updated = now
            # Refill tokens
            self.tokens = min(self.capacity, self.tokens + elapsed * self.qps)
            if self.tokens >= 1:
                self.tokens -= 1
                return
            # Need to wait
            need = 1 - self.tokens
            wait = need / self.qps
            await asyncio.sleep(wait)
            # After sleeping, consume 1 token
            self.tokens = max(0, self.tokens - 1)

class HTTPTransport:
    def __init__(self, base_url: str, timeout: float = 10.0, qps: int = 10, burst: int = 20, metrics=None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._sess: aiohttp.ClientSession | None = None
        self._rl = RateLimiter(qps=qps, burst=burst)
        self.metrics = metrics

    async def __aenter__(self):
        self._sess = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self

    async def __aexit__(self, *exc):
        if self._sess:
            await self._sess.close()
            self._sess = None

    async def request(self, method: str, path: str, **kw):
        assert self._sess is not None, "HTTPTransport must be used as async context manager"
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_exc = None
        for attempt in range(5):
            await self._rl.acquire()
            t0 = time.perf_counter()
            try:
                async with self._sess.request(method, url, **kw) as r:
                    if self.metrics:
                        self.metrics.record_latency("http_request", (time.perf_counter() - t0) * 1000)
                    if r.status >= 500:
                        last_exc = RuntimeError(f"server {r.status}")
                        raise last_exc
                    return await r.json()
            except Exception as e:
                last_exc = e
                if self.metrics:
                    self.metrics.http_retries += 1
                await sleep_backoff(attempt)
        raise RetryExhausted(str(last_exc))
