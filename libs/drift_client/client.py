import time, asyncio, uuid
from typing import AsyncIterator, Optional, Dict, Any, List
from .rest import RestAPI
from .ws import DriftWS
from .models import OrderReq, OrderResp, Position, Market, Fill
from .signer import HmacSigner
from .config import DriftConfig
from .metrics import ClientMetrics

class DriftClient:
    def __init__(self, cfg: DriftConfig, signer: HmacSigner | None = None, metrics: ClientMetrics | None = None):
        self.cfg = cfg
        self.metrics = metrics or ClientMetrics()
        self.signer = signer or HmacSigner.from_env()
        self.rest = RestAPI(cfg, signer=self.signer, metrics=self.metrics)
        self.ws = DriftWS(cfg.ws_url, metrics=self.metrics)
        self._nonce = int(time.time() * 1000)
        self._nonce_lock = asyncio.Lock()
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        await self.ws.connect()
        self._connected = True

    async def close(self) -> None:
        await self.ws.close()
        self._connected = False

    # --- helper: nonces & client IDs ---
    async def _get_nonce(self) -> int:
        async with self._nonce_lock:
            self._nonce += 1
            return self._nonce

    def _ensure_client_id(self, req: OrderReq) -> None:
        if not req.client_id:
            req.client_id = uuid.uuid4().hex[:16]

    # --- Markets/Account ---
    async def get_markets(self) -> List[Market]:
        async with self.rest as api:
            data = await api.get_markets()
        return [Market(symbol=m["symbol"], tick_size=m.get("tick_size", 0.01), step_size=m.get("step_size", 0.001)) for m in data]

    async def get_positions(self) -> List[Position]:
        async with self.rest as api:
            data = await api.get_positions()
        out: List[Position] = []
        for p in data:
            out.append(Position(symbol=p["symbol"], size=p.get("size",0.0), entry_px=p.get("entry_px",0.0), mark_price=p.get("mark_price",0.0)))
        return out

    # --- Trading ---
    async def place_order(self, req: OrderReq) -> OrderResp:
        req.nonce = req.nonce or await self._get_nonce()
        self._ensure_client_id(req)
        payload = req.model_dump()
        async with self.rest as api:
            data = await api.place_order(payload)
        self.metrics.orders_placed += 1
        return OrderResp(order_id=data.get("order_id"), status=data.get("status","accepted"), reason=data.get("reason"))

    async def cancel_order(self, order_id: str) -> bool:
        async with self.rest as api:
            data = await api.cancel_order(order_id)
        return bool(data.get("ok", True))

    async def cancel_all(self, market: Optional[str]=None) -> int:
        async with self.rest as api:
            data = await api.cancel_all(market)
        return int(data.get("cancelled", 0))

    # --- Streams (fanout) ---
    async def stream_trades(self, market: str) -> AsyncIterator[Dict[str, Any]]:
        async for msg in self.ws.stream("trades", market=market):
            yield msg

    async def stream_orderbook(self, market: str, depth: int=50) -> AsyncIterator[Dict[str, Any]]:
        async for msg in self.ws.stream("orderbook", market=market, depth=depth):
            yield msg

    async def stream_account(self) -> AsyncIterator[Dict[str, Any]]:
        async for msg in self.ws.stream("account"):
            yield msg

    # --- Batch ops ---
    async def place_orders_batch(self, reqs: List[OrderReq]) -> List[OrderResp]:
        tasks = [self.place_order(r) for r in reqs[:10]]
        res = await asyncio.gather(*tasks, return_exceptions=True)
        out: List[OrderResp] = []
        for r in res:
            if isinstance(r, Exception):
                out.append(OrderResp(order_id=None, status="rejected", reason=str(r)))
            else:
                out.append(r)
        return out
