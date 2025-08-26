from __future__ import annotations
import os
import time
from typing import Any, Dict, Optional

class DriftClient:
    """Thin client wrapper.
    Default driver is 'swift' (HTTP/WebSocket sidecar). Switch to 'driftpy' when wiring direct.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.driver = (config.get("driver") or os.getenv("DRIVER") or "swift").lower()

    def connect(self) -> None:
        # Stubbed; add WS subscriptions / HTTP health checks here
        print(f"[DriftClient] connect() using driver={self.driver}")

    def get_orderbook(self, symbol: str) -> Dict[str, Any]:
        # Return a fake orderbook shape for now
        return {
            "symbol": symbol,
            "bids": [[100.0, 10.0]],
            "asks": [[100.2, 10.0]],
            "ts": time.time(),
            "stub": True,
        }

    def place_order(self, symbol: str, side: str, price: float, size: float, post_only: bool = True) -> Dict[str, Any]:
        # Stubbed; add Swift or DriftPy call here
        print(f"[DriftClient] place_order {side} {size}@{price} {symbol} post_only={post_only}")
        return {"ok": True, "id": f"stub-{int(time.time()*1000)}"}

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        # Stubbed; add Swift or DriftPy call here
        print(f"[DriftClient] cancel_order id={order_id}")
        return {"ok": True}
