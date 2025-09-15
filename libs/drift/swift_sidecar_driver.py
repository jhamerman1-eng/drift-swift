from __future__ import annotations
import uuid
import httpx
from typing import Any, Dict, Optional

# Import protocol for type checking
try:
    from libs.types.interfaces import SidecarDriverProtocol
except ImportError:
    # Fallback for when libs.types is not available
    SidecarDriverProtocol = object

class SwiftSidecarDriver(SidecarDriverProtocol):
    """
    Minimal client for the Swift MM Sidecar.
    - place_order(envelope) -> dict (ack)
    - cancel_order(order_id) -> dict (ack)
    - health() -> dict
    """
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout_s: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._timeout = timeout_s
        self._client = httpx.Client(timeout=self._timeout)

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def health(self) -> Dict[str, Any]:
        r = self._client.get(f"{self.base_url}/health")
        r.raise_for_status()
        return r.json()

    def place_order(self, envelope: Dict[str, Any], *, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """
        envelope keys expected:
          - message (signed Swift envelope payload, base64/hex)
          - signature (base64/hex)
          - market_index (int)
          - market_type ("perp"|"spot"|"oracle")
          - taker_authority (pubkey string)
        """
        headers = self._headers()
        headers["Idempotency-Key"] = idempotency_key or str(uuid.uuid4())
        r = self._client.post(f"{self.base_url}/orders", json=envelope, headers=headers)
        r.raise_for_status()
        return r.json()

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        r = self._client.post(f"{self.base_url}/orders/{order_id}/cancel", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def order_status(self, order_id: str) -> Dict[str, Any]:
        """Retrieve sidecar's status for a previously submitted order."""
        r = self._client.get(f"{self.base_url}/orders/{order_id}/status", headers=self._headers())
        r.raise_for_status()
        # Some upstreams return text; attempt JSON parse
        try:
            return r.json()
        except Exception:
            return {"status": "unknown", "raw": r.text}

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass




