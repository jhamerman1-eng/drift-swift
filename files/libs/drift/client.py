"""
Thin Drift client wrapper for v0.9 (driftpy/anchorpy).
Falls back to safe stubs if dependencies are missing so tests/imports don't explode.
"""

from __future__ import annotations
import os
import json
import time
from dataclasses import dataclass
from typing import Optional, Any

try:
    # Optional imports; code paths guarded if missing
    import driftpy
    from driftpy.drift_client import DriftClient as _DriftClient
    from solana.rpc.async_api import AsyncClient as _AsyncClient
    from solana.keypair import Keypair
    from anchorpy import Provider, Wallet
    _HAVE_DRIFTPY = True
except Exception:  # pragma: no cover
    _HAVE_DRIFTPY = False
    _DriftClient = object  # type: ignore
    _AsyncClient = object  # type: ignore
    Keypair = object  # type: ignore
    Provider = object  # type: ignore
    Wallet = object  # type: ignore


@dataclass
class DriftConfig:
    rpc_url: str
    ws_url: Optional[str] = None
    wallet_path: Optional[str] = None
    env: str = "testnet"
    market: str = "SOL-PERP"


class DriftClient:
    def __init__(self, cfg: DriftConfig):
        self.cfg = cfg
        self._client: Optional[_DriftClient] = None
        self._connected = False

    def _load_keypair(self) -> Any:
        path = os.path.expanduser(self.cfg.wallet_path or "")
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"Wallet not found at: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            # solana-keygen json array
            from solana.keypair import Keypair  # type: ignore
            return Keypair.from_secret_key(bytes(data))
        raise ValueError("Unsupported keypair format (expect solana-keygen JSON array)")

    async def connect(self):
        if not _HAVE_DRIFTPY:
            raise RuntimeError("driftpy/anchorpy not installed. Please install dependencies.")
        kp = self._load_keypair()
        wallet = Wallet(kp)  # type: ignore
        provider = Provider(await _AsyncClient(self.cfg.rpc_url), wallet)  # type: ignore
        # NOTE: driftpy API evolves; adjust as needed
        self._client = _DriftClient(provider)  # type: ignore
        # If markets/feeds need subscription, do it here (pseudo-call):
        # await self._client.subscribe()
        self._connected = True

    async def close(self):
        self._connected = False
        # if self._client: await self._client.unsubscribe()

    async def place_post_only(self, market: Optional[str] = None, price: Optional[float] = None, size: float = 0.1, side: str = "buy"):
        """
        Place a post-only limit order (placeholder). Adjust to the actual driftpy API.
        """
        if not self._connected:
            raise RuntimeError("Not connected")
        # Pseudocode; replace with proper driftpy order type
        # await self._client.place_order(market, price, size, side, post_only=True)
        return {"ok": True, "market": market or self.cfg.market, "price": price, "size": size, "side": side, "post_only": True}

    async def cancel_all(self, market: Optional[str] = None):
        if not self._connected:
            raise RuntimeError("Not connected")
        # await self._client.cancel_all_orders(market or self.cfg.market)
        return {"ok": True}

    async def get_position(self, market: Optional[str] = None):
        if not self._connected:
            raise RuntimeError("Not connected")
        # pos = await self._client.get_position(market or self.cfg.market)
        # return pos
        return {"market": market or self.cfg.market, "base": 0.0, "pnl": 0.0}

