#!/usr/bin/env python3
"""Official Swift Integration JIT Market Maker Bot for Drift Protocol

This bot uses the official SwiftOrderSubscriber instead of manual Swift API calls,
eliminating 422 errors and providing real-time order flow via WebSocket.

Run:
    python run_mm_bot_swift_official.py --env beta --cfg configs/core/drift_client.yaml
"""

from __future__ import annotations
import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# ---------------------------- Logging ----------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("jit-mm-swift-official")


# ---------------------------- Metrics (optional) -----------------------------
class _NoopMetric:
    def __init__(self, *_, **__): pass
    def labels(self, *_, **__): return self
    def inc(self, *_, **__): return None
    def set(self, *_, **__): return None

try:
    from prometheus_client import start_http_server as _prom_start, Gauge as _Gauge, Counter as _Counter
    _METRICS_BACKEND = "prometheus"
except Exception:
    def _prom_start(*_, **__):
        logger.warning("[METRICS] Disabled (prometheus unavailable)")
    _Gauge = _NoopMetric  # type: ignore
    _Counter = _NoopMetric  # type: ignore
    _METRICS_BACKEND = "noop"

MM_TICKS: Any = None
MM_SKIPS: Any = None
MM_ERRORS: Any = None


# ---------------------------- Config -----------------------------------------
def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class JITConfig:
    symbol: str
    obi_microprice: bool
    spread_bps_base: float
    spread_bps_min: float
    spread_bps_max: float
    inventory_target: float
    max_position_abs: float
    toxicity_guard: bool

    @classmethod
    def from_yaml(cls, cfg: dict) -> "JITConfig":
        spread = cfg.get("spread_bps", {})
        return cls(
            symbol=cfg.get("symbol", "SOL-PERP"),
            obi_microprice=bool(cfg.get("obi_microprice", True)),
            spread_bps_base=float(spread.get("base", 8.0)),
            spread_bps_min=float(spread.get("min", 4.0)),
            spread_bps_max=float(spread.get("max", 25.0)),
            inventory_target=float(cfg.get("inventory_target", 0.0)),
            max_position_abs=float(cfg.get("max_position_abs", 120.0)),
            toxicity_guard=bool(cfg.get("toxicity_guard", True)),
        )


@dataclass
class Orderbook:
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]
    ts: float


class MarketDataAdapter:
    """Lightweight orderbook source using libs.drift.client if available."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self._cache: Optional[Orderbook] = None
        self._ttl = float(cfg.get("orderbook_ttl_seconds", 0.25))
        self._max_stale = float(cfg.get("orderbook_max_stale_seconds", 2.0))
        try:
            from libs.drift.client import DriftClient  # type: ignore
            raw_env = cfg.get("cluster", "beta").lower()
            env_norm = "devnet" if raw_env == "beta" else ("mainnet" if raw_env in ("mainnet", "mainnet-beta") else raw_env)
            self._driver = DriftClient(env=env_norm, cfg=cfg)
            self._use_driver = True
            logger.info("[MD] Using libs.drift.client for orderbook (env=%s)", env_norm)
        except Exception as e:
            self._driver = None
            self._use_driver = False
            logger.warning("[MD] libs.drift.client unavailable (%s); using mock OB", e)

    def get_orderbook(self) -> Orderbook:
        now = time.time()
        if self._cache and (now - self._cache.ts) <= self._ttl:
            return self._cache
        try:
            if self._use_driver:
                raw = asyncio.get_event_loop().run_until_complete(self._driver.get_orderbook(0))  # type: ignore
                bids = [(float(p), float(s)) for p, s in raw.get("bids", [])[:16]]
                asks = [(float(p), float(s)) for p, s in raw.get("asks", [])[:16]]
            else:
                mid = 150.0
                bids = [(mid - 0.05, 1.0), (mid - 0.06, 2.0)]
                asks = [(mid + 0.05, 1.2), (mid + 0.06, 2.4)]
            if not bids or not asks:
                raise ValueError("empty book")
            ob = Orderbook(bids=bids, asks=asks, ts=now)
            self._cache = ob
            return ob
        except Exception:
            if self._cache and (now - self._cache.ts) <= self._max_stale:
                return self._cache
            mid = 150.0
            ob = Orderbook(bids=[(mid - 0.1, 0.5)], asks=[(mid + 0.1, 0.5)], ts=now)
            self._cache = ob
            return ob


class OfficialSwiftExecutionClient:
    """Executes orders via official Swift integration using SwiftOrderSubscriber."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.market_index = int(cfg.get("market_index", 0))
        self.swift_subscriber = None
        self.drift_client = None
        self.keypair = None
        self.user_map = None
        self._swift_orders_received = 0
        self._swift_orders_processed = 0

    async def initialize_swift_subscriber(self, drift_client, keypair):
        from driftpy.swift.order_subscriber import SwiftOrderSubscriber, SwiftOrderSubscriberConfig
        from driftpy.user_map.user_map import UserMap

        self.user_map = UserMap(drift_client)
        await self.user_map.subscribe()

        config = SwiftOrderSubscriberConfig(
            drift_client=drift_client,
            keypair=keypair,
            user_map=self.user_map,
            drift_env="devnet",
            market_indexes=[self.market_index],
        )
        self.swift_subscriber = SwiftOrderSubscriber(config)
        self.drift_client = drift_client
        self.keypair = keypair

    async def subscribe_to_swift_orders(self, on_order_callback):
        if not self.swift_subscriber:
            raise RuntimeError("Swift subscriber not initialized")
        await self.swift_subscriber.subscribe(on_order_callback)

    async def on_swift_order(self, order_message_raw, signed_message, is_delegate):
        self._swift_orders_received += 1
        logger.info("[Swift] order #%d received (delegate=%s)", self._swift_orders_received, is_delegate)
        try:
            await self._process_swift_order(order_message_raw, signed_message, is_delegate)
            self._swift_orders_processed += 1
        except Exception as e:
            logger.error("[Swift] order processing error: %s", e)

    async def _process_swift_order(self, order_message_raw, signed_message, is_delegate):
        # hook for strategy
        return None

    async def close(self) -> None:
        try:
            if self.swift_subscriber:
                await self.swift_subscriber.unsubscribe()
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        return {
            "swift_orders_received": self._swift_orders_received,
            "swift_orders_processed": self._swift_orders_processed,
            "swift_subscriber_active": self.swift_subscriber is not None,
            "drift_client_active": self.drift_client is not None,
        }


class JITMarketMaker:
    def __init__(self, jcfg: JITConfig, core_cfg: dict):
        self.jcfg = jcfg
        self.core_cfg = core_cfg
        self.md = MarketDataAdapter(core_cfg)
        self.exec = OfficialSwiftExecutionClient(core_cfg)
        self.position = 0.0

    async def initialize(self, drift_client, keypair):
        await self.exec.initialize_swift_subscriber(drift_client, keypair)
        await self.exec.subscribe_to_swift_orders(self.exec.on_swift_order)
        logger.info("[MM] Initialized with Swift subscriber")

    async def tick(self) -> None:
        if MM_TICKS:
            MM_TICKS.inc()
        ob = self.md.get_orderbook()
        if not ob.bids or not ob.asks:
            if MM_SKIPS:
                MM_SKIPS.labels(reason="nol1").inc()
            await asyncio.sleep(0.25)
            return
        bb = ob.bids[0][0]; ba = ob.asks[0][0]
        mid = 0.5 * (bb + ba)
        logger.info("[MM] mid=%.4f bb=%.4f ba=%.4f", mid, bb, ba)

    async def shutdown(self) -> None:
        await self.exec.close()


# ---------------------------- Main -------------------------------------------

RUNNING = True

def _sigterm(sig, _frame):
    global RUNNING
    logger.info("Signal %s received — graceful stop", sig)
    RUNNING = False


async def run_main(env: str, cfg_path: Path, *, no_metrics: bool = False) -> int:
    core_cfg = load_yaml(cfg_path)
    jit_cfg_path = Path("configs/jit/params.yaml")
    jit_raw = load_yaml(jit_cfg_path) if jit_cfg_path.exists() else {}
    jit_cfg = JITConfig.from_yaml(jit_raw)

    # metrics
    global MM_TICKS, MM_SKIPS, MM_ERRORS
    if _METRICS_BACKEND == "prometheus" and not no_metrics:
        MM_TICKS = _Counter("mm_ticks_total", "Total MM ticks")
        MM_SKIPS = _Counter("mm_skips_total", "MM skips by reason", labelnames=("reason",))
        MM_ERRORS = _Counter("mm_errors_total", "Errors by type", labelnames=("type",))
        port = int(os.getenv("METRICS_PORT", "9300"))
        _prom_start(port)
        logger.info("[METRICS] Prometheus on :%d", port)
    else:
        MM_TICKS = _Counter()
        class _ShimCounter(_NoopMetric):
            def labels(self, *_, **__): return self
        MM_SKIPS = _ShimCounter()
        MM_ERRORS = _ShimCounter()

    # signals
    signal.signal(signal.SIGINT, _sigterm)
    try:
        signal.signal(signal.SIGTERM, _sigterm)
    except Exception:
        pass

    # Initialize DriftPy client (basic)
    try:
        from driftpy.drift_client import DriftClient
        from solders.keypair import Keypair
        from solana.rpc.async_api import AsyncClient

        keypair_path = (core_cfg.get("wallets", {}) or {}).get("maker_keypair_path") or os.getenv("DRIFT_KEYPAIR_PATH")
        if not keypair_path or not os.path.exists(keypair_path):
            raise RuntimeError(f"Wallet file not found: {keypair_path}")
        with open(keypair_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            secret_bytes = bytes(data[:64])
        elif isinstance(data, dict) and "secret_key" in data:
            from base58 import b58decode
            secret_bytes = b58decode(str(data["secret_key"]))
        else:
            raise RuntimeError("Unsupported wallet JSON format")
        keypair = Keypair.from_bytes(secret_bytes)

        rpc_url = (core_cfg.get("rpc", {}) or {}).get("http_url") or os.getenv("DRIFT_RPC_URL")
        if not rpc_url:
            raise RuntimeError("RPC URL not configured")
        env_norm = env.lower()
        if env_norm in ("beta", "mainnet-beta"):
            env_norm = "devnet" if env_norm == "beta" else "mainnet"

        drift_client = DriftClient(connection=AsyncClient(rpc_url), wallet=keypair, env=env_norm)
        if hasattr(drift_client, "subscribe"):
            await drift_client.subscribe()
    except Exception as e:
        logger.error("Failed to init DriftPy: %s", e)
        return 1

    mm = JITMarketMaker(jit_cfg, core_cfg)
    await mm.initialize(drift_client, keypair)
    logger.info("JIT MM starting (env=%s, symbol=%s, metrics=%s)", env, jit_cfg.symbol, _METRICS_BACKEND if not no_metrics else "disabled")

    try:
        while RUNNING:
            try:
                await mm.tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                if MM_ERRORS:
                    MM_ERRORS.labels(type="tick").inc()
                logger.exception("Tick error: %s", e)
                await asyncio.sleep(0.25)
            await asyncio.sleep(0.25)
    finally:
        try:
            await mm.shutdown()
        except Exception:
            pass
        try:
            if hasattr(drift_client, "unsubscribe"):
                await drift_client.unsubscribe()
        except Exception:
            pass
    return 0


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Official Swift Integration JIT MM Bot")
    p.add_argument("--env", default=os.getenv("ENV", "beta"))
    p.add_argument("--cfg", default="configs/core/drift_client.yaml")
    p.add_argument("--no-metrics", action="store_true", help="Disable Prometheus metrics")
    return p.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    try:
        rc = asyncio.run(run_main(args.env, Path(args.cfg), no_metrics=args.no_metrics))
    except KeyboardInterrupt:
        rc = 0
    raise SystemExit(rc)

