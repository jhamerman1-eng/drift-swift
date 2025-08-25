import asyncio, json, logging
import websockets
from .errors import WSClosed

logger = logging.getLogger(__name__)

class DriftWS:
    def __init__(self, url: str, metrics=None):
        self.url = url
        self._ws = None
        self._lock = asyncio.Lock()
        self.metrics = metrics

    async def connect(self):
        async with self._lock:
            if self._ws:
                return
            self._ws = await websockets.connect(self.url, ping_interval=15, ping_timeout=10)

    async def close(self):
        async with self._lock:
            if self._ws:
                await self._ws.close()
                self._ws = None

    async def subscribe(self, channel: str, **params) -> None:
        if not self._ws:
            await self.connect()
        await self._ws.send(json.dumps({"op": "subscribe", "ch": channel, "params": params}))

    async def stream(self, channel: str, **params):
        reconnect_delay = 1.0
        while True:
            try:
                if not self._ws:
                    await self.connect()
                await self.subscribe(channel, **params)
                reconnect_delay = 1.0
                async for msg in self._ws:
                    yield json.loads(msg)
            except Exception as e:
                logger.error(f"WS error: {e}; reconnecting in {reconnect_delay:.2f}s")
                if self.metrics:
                    self.metrics.ws_reconnects += 1
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 30.0)
                try:
                    await self.connect()
                except Exception:
                    pass
