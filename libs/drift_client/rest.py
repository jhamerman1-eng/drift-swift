from typing import Any, Dict, List, Optional
from .transport import HTTPTransport
from .config import DriftConfig
from .signer import HmacSigner

class RestAPI:
    def __init__(self, cfg: DriftConfig, signer: HmacSigner, metrics=None):
        self.cfg = cfg
        self.metrics = metrics
        self.signer = signer
        self._http: HTTPTransport | None = None

    async def __aenter__(self):
        self._http = HTTPTransport(self.cfg.http_url, qps=self.cfg.qps_limit, burst=self.cfg.burst, metrics=self.metrics)
        await self._http.__aenter__()
        return self

    async def __aexit__(self, *exc):
        if self._http:
            await self._http.__aexit__(*exc)
            self._http = None

    # Placeholder endpoints; wire actual Drift routes & headers
    async def get_markets(self) -> List[Dict[str, Any]]:
        return await self._http.request("GET", "/v1/markets")  # type: ignore

    async def get_positions(self) -> List[Dict[str, Any]]:
        return await self._http.request("GET", "/v1/positions")  # type: ignore

    async def place_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._http.request("POST", "/v1/orders", json=payload)  # type: ignore

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return await self._http.request("DELETE", f"/v1/orders/{order_id}")  # type: ignore

    async def cancel_all(self, market: Optional[str]=None) -> Dict[str, Any]:
        path = "/v1/orders/cancel_all" if not market else f"/v1/orders/cancel_all?market={market}"
        return await self._http.request("POST", path)  # type: ignore
