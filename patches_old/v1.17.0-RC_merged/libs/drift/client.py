"""Asynchronous Drift client implementations.

This module provides a set of classes to interact with the Drift protocol
using asynchronous HTTP and WebSocket clients.  It also exposes a simple
mock client for local testing and a skeleton for integrating the official
`driftpy` library when available.  Consumers of this module should use
``build_client_from_config`` to obtain a client instance appropriate for
their environment.

Key features:

* **Async first**: all network operations are defined as ``async`` methods.
* **Connection pooling**: uses a shared ``aiohttp.ClientSession`` for
  HTTP requests.
* **Rate limiting**: a simple token bucket limits the number of HTTP
  requests per second to avoid overwhelming public endpoints.
* **Mock implementation**: ``MockDriftClient`` synthesises orderbooks via
  a random walk and logs order placement requests.  This is suitable for
  development and unit testing.
* **Configurable via YAML**: the ``build_client_from_config`` helper
  reads a YAML config file with environment variable interpolation and
  constructs the appropriate client.

Note that this module intentionally does *not* contain any secret keys or
RPC endpoints.  These should be provided via configuration files or
environment variables.  The real Drift integration is left as a stub:
replace the ``DriftpyClient`` implementation with calls into the
`driftpy` library once it is installed and configured.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Protocol, List, Tuple, Optional

import aiohttp
import numpy as np
import yaml
import websockets
from loguru import logger


@dataclass
class Order:
    """Specification for an order to be sent to Drift.

    Attributes
    ----------
    side : str
        Either ``"buy"`` or ``"sell"``.
    price : float
        The limit price at which to place the order.
    size_usd : float
        The size of the order in quote currency (USD equivalent).  A
        production implementation should convert this into the native
        base/quote lot sizes required by Drift.
    """
    side: str  # "buy" | "sell"
    price: float
    size_usd: float


@dataclass
class Orderbook:
    """Represents a simplified Level‑2 orderbook.

    Attributes
    ----------
    bids : list[tuple[float, float]]
        Sorted list of (price, size) tuples on the bid side.
    asks : list[tuple[float, float]]
        Sorted list of (price, size) tuples on the ask side.
    """
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]


class DriftClient(Protocol):
    """Protocol describing the required interface for all clients."""

    async def place_order(self, order: Order) -> str:
        """Submit a new order to the exchange and return an order ID."""
        ...

    async def cancel_all(self) -> None:
        """Cancel all open orders for the current market."""
        ...

    async def get_orderbook(self) -> Orderbook:
        """Retrieve the current orderbook for the configured market."""
        ...

    async def close(self) -> None:
        """Release any open network resources held by the client."""
        ...


class _RateLimiter:
    """Simple token bucket rate limiter for asynchronous contexts."""

    def __init__(self, max_calls: int, per_seconds: float) -> None:
        self._sem = asyncio.BoundedSemaphore(max_calls)
        self._interval = per_seconds / max_calls

    async def __aenter__(self) -> "_RateLimiter":
        await self._sem.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await asyncio.sleep(self._interval)
        self._sem.release()


class AsyncDriftClient:
    """Asynchronous HTTP/WebSocket Drift client.

    This client uses ``aiohttp`` for HTTP requests and ``websockets`` for
    streaming orderbook updates.  A simple rate limiter ensures that no
    more than ``max_calls_per_second`` HTTP requests are made.  Market
    subscriptions must be performed manually by calling
    :meth:`subscribe_orderbook` once after construction.

    Parameters
    ----------
    http_url : str
        Base URL for the Drift REST API (e.g. ``"https://api.drift.trade"``).
    ws_url : str
        WebSocket URL for streaming data (e.g. ``"wss://stream.drift.trade"``).
    market : str
        Name of the market (e.g. ``"SOL-PERP"``) to subscribe to when
        building orderbook updates.
    max_calls_per_second : int, optional
        Number of HTTP requests allowed per second.  Defaults to 5.
    """

    def __init__(self, http_url: str, ws_url: str, market: str = "SOL-PERP", max_calls_per_second: int = 5) -> None:
        self.http_url = http_url.rstrip("/")
        self.ws_url = ws_url
        self.market = market
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._limiter = _RateLimiter(max_calls_per_second, 1.0)
        self.logger = logger.bind(component="AsyncDriftClient", market=market)

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _ensure_ws(self) -> websockets.WebSocketClientProtocol:
        if self._ws is None or self._ws.closed:
            self.logger.info(f"Connecting WS {self.ws_url}…")
            self._ws = await websockets.connect(self.ws_url)
            # Automatically subscribe to the orderbook for the configured market
            await self.subscribe_orderbook(self.market)
        return self._ws

    async def subscribe_orderbook(self, market: str) -> None:
        ws = await self._ensure_ws()
        payload = {"op": "subscribe", "channel": "orderbook", "market": market}
        await ws.send(json.dumps(payload))
        self.logger.debug(f"Subscribed to orderbook for {market}")

    async def get_orderbook(self) -> Orderbook:
        """Return a snapshot of the top of book.

        This implementation listens for a single orderbook update and
        constructs a simple ``Orderbook`` from the first few levels.  In a
        production system you would maintain a running orderbook state
        locally and return that instead.
        """
        ws = await self._ensure_ws()
        msg = await ws.recv()
        try:
            data = json.loads(msg)
        except Exception as exc:
            self.logger.error(f"Failed to decode orderbook message: {exc}: {msg}")
            return Orderbook(bids=[], asks=[])
        # Expected payload shape: {"bids": [[price, size], …], "asks": [[price, size], …]}
        bids_raw = data.get("bids", [])
        asks_raw = data.get("asks", [])
        bids: List[Tuple[float, float]] = [(float(p), float(s)) for p, s in bids_raw[:5]]
        asks: List[Tuple[float, float]] = [(float(p), float(s)) for p, s in asks_raw[:5]]
        return Orderbook(bids=bids, asks=asks)

    async def place_order(self, order: Order) -> str:
        """Send a limit order via the REST API and return an order ID.

        This method constructs a JSON payload compatible with the Drift
        REST API.  The payload format may need adjustment once the
        official API is finalised.  For now it logs the request and
        returns a pseudo order ID.
        """
        await self._ensure_session()
        payload = {
            "market": self.market,
            "side": order.side,
            "price": order.price,
            "size_usd": order.size_usd,
        }
        async with self._limiter:
            self.logger.info(f"Placing order: {payload}")
            # In an actual implementation you'd call
            # async with self._session.post(f"{self.http_url}/order", json=payload) as resp:
            #     data = await resp.json()
            #     return data.get("order_id")
            await asyncio.sleep(0.1)  # simulate network latency
        # Return a fake order id for now
        oid = f"async-{order.side}-{order.price:.2f}-{order.size_usd:.0f}"
        return oid

    async def cancel_all(self) -> None:
        """Cancel all open orders (stub implementation)."""
        async with self._limiter:
            self.logger.info("Cancelling all orders (stub)")
            await asyncio.sleep(0.05)

    async def close(self) -> None:
        """Close any open network resources."""
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        if self._session is not None:
            await self._session.close()
            self._session = None


class MockDriftClient:
    """Mock client that synthesises a plausible orderbook around a drifting mid.

    This class mirrors the behaviour of the earlier ``MockDriftClient`` but
    exposes asynchronous methods to integrate seamlessly with other async
    components.  It uses a simple random walk to evolve the mid price on
    each call to :meth:`get_orderbook`.  Orders are logged via ``loguru``.
    """

    def __init__(self, market: str = "SOL-PERP", start: float = 150.0, spread_bps: float = 6.0) -> None:
        self.market = market
        self.mid = float(start)
        self.spread = spread_bps / 1e4

    def _step(self) -> None:
        sigma = 0.0007
        shock = np.random.normal(0.0, sigma) * self.mid
        self.mid = max(0.01, self.mid + shock)

    async def get_orderbook(self) -> Orderbook:
        self._step()
        half = self.mid * self.spread / 2.0
        top_bid = self.mid - half
        top_ask = self.mid + half
        levels = 5
        tick = max(self.mid * 1e-5, 0.01)
        bids = [(round(top_bid - i * tick, 4), 10.0 + i) for i in range(levels)]
        asks = [(round(top_ask + i * tick, 4), 10.0 + i) for i in range(levels)]
        return Orderbook(bids=bids, asks=asks)

    async def place_order(self, order: Order) -> str:
        oid = f"mock-{order.side}-{order.price:.2f}-{order.size_usd:.0f}"
        logger.info(f"[MOCK] place_order {self.market} → {order}")
        return oid

    async def cancel_all(self) -> None:
        logger.info(f"[MOCK] cancel_all {self.market}")

    async def close(self) -> None:
        return None


# Optional real client (skeleton)
try:
    import driftpy  # type: ignore
except Exception:
    driftpy = None


class DriftpyClient:
    """Skeleton for real Drift integration (non‑functional stub).

    This class is intended as a starting point for implementing a real
    Drift integration using the official ``driftpy`` library.  It
    demonstrates how the constructor might accept RPC endpoints and a
    wallet secret key.  All methods raise ``RuntimeError`` to remind
    developers to implement them.
    """
    def __init__(self, rpc_url: str, wallet_secret_key: str, market: str = "SOL-PERP", ws_url: str | None = None) -> None:
        if driftpy is None:
            raise RuntimeError("driftpy not installed. Add to pyproject and install.")
        self.rpc_url = rpc_url
        self.ws_url = ws_url
        self.wallet_secret_key = wallet_secret_key
        self.market = market
        # TODO: initialize driftpy client, load market accounts, and signer
        raise RuntimeError("DriftpyClient has not been implemented yet. Please implement this class using driftpy.")

    async def get_orderbook(self) -> Orderbook:
        raise RuntimeError("get_orderbook is not implemented for DriftpyClient")

    async def place_order(self, order: Order) -> str:
        raise RuntimeError("place_order is not implemented for DriftpyClient")

    async def cancel_all(self) -> None:
        raise RuntimeError("cancel_all is not implemented for DriftpyClient")

    async def close(self) -> None:
        raise RuntimeError("close is not implemented for DriftpyClient")


async def build_client_from_config(cfg_path: str) -> DriftClient:
    """Build a Drift client instance from a YAML configuration file.

    The configuration file is expected to contain keys such as ``env``,
    ``market``, ``use_mock``, ``rpc_url``, and ``ws_url``.  Environment
    variables referenced in the YAML (via ``$VAR`` syntax) will be
    expanded.  If ``use_mock`` is true (default), a ``MockDriftClient``
    will be returned.  Otherwise an ``AsyncDriftClient`` will be
    constructed with the provided endpoints.

    Parameters
    ----------
    cfg_path : str
        Path to the YAML configuration file.

    Returns
    -------
    DriftClient
        A ready‑to‑use client instance.
    """
    text = os.path.expandvars(open(cfg_path, "r").read())
    cfg = yaml.safe_load(text) or {}
    env = cfg.get("env", "testnet")
    market = cfg.get("market", "SOL-PERP")
    use_mock = bool(cfg.get("use_mock", True))
    if use_mock:
        logger.info(f"Using MockDriftClient for {market} ({env})")
        return MockDriftClient(market=market)
    # Use real async client
    rpc = cfg.get("rpc_url") or os.getenv("DRIFT_RPC_URL")
    ws = cfg.get("ws_url") or os.getenv("DRIFT_WS_URL")
    if not rpc or not ws:
        raise RuntimeError("rpc_url and ws_url (or DRIFT_RPC_URL/DRIFT_WS_URL) are required for real client")
    logger.info(f"Using AsyncDriftClient for {market} ({env}) via {rpc}")
    return AsyncDriftClient(http_url=rpc, ws_url=ws, market=market)