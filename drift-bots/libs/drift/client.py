from dataclasses import dataclass
from typing import Protocol, List, Tuple
from loguru import logger
import os
import random
import yaml

@dataclass
class Order:
    side: str  # "buy" | "sell"
    price: float
    size_usd: float

@dataclass
class Orderbook:
    bids: List[Tuple[float, float]]  # (price, size)
    asks: List[Tuple[float, float]]

class DriftClient(Protocol):
    def place_order(self, order: Order) -> str:
        ...
    def cancel_all(self) -> None:
        ...
    def get_orderbook(self) -> Orderbook:
        ...
    async def close(self) -> None:
        ...

class MockDriftClient:
    """Mock client for v0.2. Synthesizes a plausible orderbook around a drifting mid."""
    def __init__(self, market: str = "SOL-PERP", start: float = 150.0, spread_bps: float = 6.0):
        self.market = market
        self.mid = float(start)
        self.spread = spread_bps / 1e4

    def _step(self) -> None:
        # random‑walk mid with mild volatility (~7 bps sigma)
        sigma = 0.0007
        shock = random.gauss(0, sigma) * self.mid
        self.mid = max(0.01, self.mid + shock)

    def get_orderbook(self) -> Orderbook:
        self._step()
        half = self.mid * self.spread / 2
        top_bid = self.mid - half
        top_ask = self.mid + half
        levels = 5
        tick = max(self.mid * 1e-5, 0.01)
        bids = [(round(top_bid - i * tick, 4), 10.0 + i) for i in range(levels)]
        asks = [(round(top_ask + i * tick, 4), 10.0 + i) for i in range(levels)]
        return Orderbook(bids=bids, asks=asks)

    def place_order(self, order: Order) -> str:
        oid = f"mock-{order.side}-{order.price:.2f}-{order.size_usd:.0f}"
        logger.info(f"[MOCK] place_order {self.market} → {order}")
        return oid

    def cancel_all(self) -> None:
        logger.info(f"[MOCK] cancel_all {self.market}")

    async def close(self) -> None:
        return None

# Optional real client (skeleton)
try:
    import driftpy  # type: ignore
except Exception:
    driftpy = None

class DriftpyClient:
    """Skeleton for real Drift integration. Fill RPC, wallet, market wiring in v0.3."""
    def __init__(self, rpc_url: str, wallet_secret_key: str, market: str = "SOL-PERP", ws_url: str | None = None):
        if driftpy is None:
            raise RuntimeError("driftpy not installed. Add to pyproject and install.")
        self.rpc_url = rpc_url
        self.ws_url = ws_url
        self.wallet_secret_key = wallet_secret_key
        self.market = market
        # TODO: initialize drift client, load market accounts, signer, etc.

    def place_order(self, order: Order) -> str:
        # TODO: translate USD size to contracts/quote size, build instruction, send TX
        return "txsig_placeholder"

    def cancel_all(self) -> None:
        # TODO
        return None

    def get_orderbook(self) -> Orderbook:
        # TODO: fetch from Drift markets/orderbook accounts
        return Orderbook(bids=[], asks=[])

    async def close(self) -> None:
        # TODO: close websockets if any
        return None

async def build_client_from_config(cfg_path: str) -> DriftClient:
    """Builder reads YAML with env‑var interpolation and returns a client."""
    text = os.path.expandvars(open(cfg_path, "r").read())
    cfg = yaml.safe_load(text)
    env = cfg.get("env", "testnet")
    market = cfg.get("market", "SOL-PERP")
    use_mock = bool(cfg.get("use_mock", True))

    if use_mock:
        logger.info(f"Using MockDriftClient for {market} ({env})")
        return MockDriftClient(market=market)

    rpc = cfg.get("rpc_url") or os.getenv("DRIFT_RPC_URL")
    ws = cfg.get("ws_url") or os.getenv("DRIFT_WS_URL")
    secret = cfg.get("wallet_secret_key") or os.getenv("DRIFT_KEYPAIR_PATH")
    if not rpc or not secret:
        raise RuntimeError("rpc_url and wallet_secret_key/DRIFT_KEYPAIR_PATH are required for real client")
    logger.info(f"Using DriftpyClient for {market} ({env}) via {rpc}")
    return DriftpyClient(rpc_url=rpc, wallet_secret_key=secret, market=market, ws_url=ws)

if __name__ == "__main__":
    import asyncio
    async def _smoke():
        client = await build_client_from_config(os.getenv("DRIFT_CFG", "configs/core/drift_client.yaml"))
        ob = client.get_orderbook()
        if ob.bids and ob.asks:
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
            logger.info(f"Top‑of‑book mid={mid:.4f} (b={ob.bids[0][0]:.4f} a={ob.asks[0][0]:.4f})")
    asyncio.run(_smoke())
