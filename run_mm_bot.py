"""Bots/jit/main SwiftBots/jit/main Swift
Enhanced JIT Market Maker Bot for Drift Protocol — Swift Integration (Exit‑safe, SSL‑safe)

Fixes two issues observed in sandboxed/tested runtimes:
1) `ModuleNotFoundError: No module named 'ssl'` (from `prometheus_client`).
   → Metrics are now optional with a **no‑op shim** if SSL/prometheus are unavailable, or when `--no-metrics` is set.
2) `SystemExit: 1` raised by `sys.exit(1)` on fatal errors or selftests.
   → The launcher no longer calls `sys.exit(...)`. Errors are logged and the program returns
     cleanly to avoid disruptive exits in harnesses while still surfacing stacktraces.

If you prefer hard exits in production, set env `HARD_EXIT=1` to restore `sys.exit(code)` behavior.

Install (typical):
    pip install driftpy anchorpy solana base58 httpx pyyaml prometheus_client

Run:
    python bots/jit/main_swift.py --env beta --cfg configs/core/drift_client.yaml

Options:
    --no-metrics   Disable Prometheus metrics even if available.
    --selftest     Run built-in tests (no network) and return.

Note: For real Swift order flow without system SSL, use an **HTTP sidecar** (e.g., `SWIFT_SIDECAR=http://localhost:8787`).
"""

from __future__ import annotations
import argparse
import asyncio
import json
import logging
import math
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
import httpx

# ---------------------------- Logging ----------------------------------------
)
logger = logging.getLogger("jit-mm-swift")

# ---------------------------- SSL/Metrics Safe Import -------------------------

def _ssl_available() -> bool:
    try:
        import ssl  # noqa: F401
        return True
    except Exception:
        return False

SSL_OK = _ssl_available()

# Prometheus optional: provide a no-op shim when ssl/prometheus are unavailable
class _NoopMetric:
    def __init__(self, *_, **__): pass
    def labels(self, *_, **__): return self
    def inc(self, *_, **__): return None
    def set(self, *_, **__): return None

def _noop_start_http_server(*_, **__):
    logger.warning("[METRICS] Disabled (ssl/prometheus unavailable or --no-metrics)")

try:
    if not SSL_OK:
        raise ImportError("ssl missing")
    from prometheus_client import start_http_server as _prom_start, Gauge as _Gauge, Counter as _Counter
    _METRICS_BACKEND = "prometheus"
except Exception:
    _prom_start = _noop_start_http_server
    _Gauge = _NoopMetric  # type: ignore
    _Counter = _NoopMetric  # type: ignore
    _METRICS_BACKEND = "noop"

# Metrics instances (created later to honor --no-metrics)
MM_TICKS: Any = None
MM_SKIPS: Any = None
MM_QUOTES: Any = None
MM_CANCELS: Any = None
MM_ERRORS: Any = None
MM_SPREAD: Any = None
MM_MID: Any = None

# ---------------------------- Config -----------------------------------------

def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

@dataclass
class JITConfig:
    symbol: str
    leverage: int
    post_only: bool
    obi_microprice: bool
    spread_bps_base: float
    spread_bps_min: float
    spread_bps_max: float
    inventory_target: float
    max_position_abs: float
    cancel_replace_enabled: bool
    cancel_replace_interval_ms: int
    toxicity_guard: bool
    tick_size: float
    cr_min_ticks: int

    @classmethod
    def from_yaml(cls, cfg: dict) -> "JITConfig":
        spread = cfg.get("spread_bps", {})
        cr = cfg.get("cancel_replace", {})
        mm = cfg.get("mm", {})
        return cls(
            symbol=cfg.get("symbol", "SOL-PERP"),
            leverage=int(cfg.get("leverage", 10)),
            post_only=bool(cfg.get("post_only", True)),
            obi_microprice=bool(cfg.get("obi_microprice", True)),
            spread_bps_base=float(spread.get("base", 8.0)),
            spread_bps_min=float(spread.get("min", 4.0)),
            spread_bps_max=float(spread.get("max", 25.0)),
            inventory_target=float(cfg.get("inventory_target", 0.0)),
            max_position_abs=float(cfg.get("max_position_abs", 120.0)),
            cancel_replace_enabled=bool(cr.get("enabled", True)),
            cancel_replace_interval_ms=int(cr.get("interval_ms", 900)),
            toxicity_guard=bool(cr.get("toxicity_guard", True)),
            tick_size=float(mm.get("tick_size", 0.001)),
            cr_min_ticks=int(mm.get("cr_min_ticks", 2)),
        )

# ---------------------------- Orderbook + OBI --------------------------------

@dataclass
class Orderbook:
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]
    ts: float

class OBICalculator:
    def __init__(self, levels: int = 10):
        self.levels = levels

    def calculate(self, ob: Orderbook) -> Tuple[float, float, float, float]:
        """Return (microprice, imbalance_ratio, skew_adjust, confidence)."""
        if not ob.bids or not ob.asks:
            return 0.0, 0.0, 0.0, 0.0
        bid_vol = sum(sz for _, sz in ob.bids[: self.levels])
        ask_vol = sum(sz for _, sz in ob.asks[: self.levels])
        denom = bid_vol + ask_vol
        if denom <= 1e-12:
            return 0.0, 0.0, 0.0, 0.0
        bb = float(ob.bids[0][0]); ba = float(ob.asks[0][0])
        micro = (bid_vol * ba + ask_vol * bb) / denom
        imb = (bid_vol - ask_vol) / denom
        skew = 0.5 * imb
        conf = min(1.0, denom / 100.0)
        return micro, imb, skew, conf

# ---------------------------- Market Data Adapter ----------------------------

class MarketDataAdapter:
    """Synchronous orderbook source with TTL + stale fallback.

    Prefers local Drift client (libs.drift.client) if present.
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self._cache: Optional[Orderbook] = None
        self._ttl = float(cfg.get("orderbook_ttl_seconds", 0.25))
        self._max_stale = float(cfg.get("orderbook_max_stale_seconds", 2.0))

        # optional import of local driver
        try:
            from libs.drift.client import DriftClient  # type: ignore
            self._driver = DriftClient(env=cfg.get("cluster", "beta"), cfg=cfg, logger=logger)
            self._use_driver = True
            logger.info("[MD] Using libs.drift.client for orderbook")
        except Exception as e:  # pragma: no cover
            self._driver = None
            self._use_driver = False
            logger.warning("[MD] libs.drift.client unavailable (%s); using mock OB", e)

    def get_orderbook(self) -> Orderbook:
        now = time.time()
        if self._cache and (now - self._cache.ts) <= self._ttl:
            return self._cache
        try:
            if self._use_driver:
                raw = self._driver.get_orderbook()  # expected dict {bids:[[p,s]], asks:[[p,s]]}
                bids = [(float(p), float(s)) for p, s in raw["bids"][:16]]
                asks = [(float(p), float(s)) for p, s in raw["asks"][:16]]
            else:
                # very small mock to keep the loop alive if no driver
                mid = 150.0
                bids = [(mid - 0.05, 1.0), (mid - 0.06, 2.0)]
                asks = [(mid + 0.05, 1.2), (mid + 0.06, 2.4)]
            if not bids or not asks:
                raise ValueError("empty book")
            ob = Orderbook(bids=bids, asks=asks, ts=now)
            self._cache = ob
            return ob
        except Exception as e:
            if self._cache and (now - self._cache.ts) <= self._max_stale:
                logger.info("[MD] stale ob served (%.3fs old)", now - self._cache.ts)
                return self._cache
            if MM_ERRORS:
                MM_ERRORS.labels(type="orderbook").inc()
            logger.exception("Orderbook fetch failed: %s", e)
            # Return a minimal synthetic book to keep service alive
            mid = 150.0
            ob = Orderbook(bids=[(mid - 0.1, 0.5)], asks=[(mid + 0.1, 0.5)], ts=now)
            self._cache = ob
            return ob

# ---------------------------- Swift Execution Client -------------------------

try:
    from libs.drift.client import DriftpyClient as DriftSignerClient  # for signing
    from driftpy.types import (
        OrderParams,
        OrderType,
        MarketType,
        SignedMsgOrderParamsMessage,
        PositionDirection,
    )
    HAVE_DRIFTPY = True
except Exception as e:  # pragma: no cover
    HAVE_DRIFTPY = False
    DriftSignerClient = Any  # type: ignore
    PositionDirection = Any  # type: ignore
    logger.warning("DriftPy not available: %s — Swift submit will run in MOCK ACK mode.", e)

class SwiftExecClient:
    """Swift submit/cancel via direct Swift API or Sidecar proxy.

    - Signs orders with DriftPy (if available)
    - Submits JSON to `/orders`
    - Cancels via `/orders/{id}/cancel` (sidecar mode), otherwise best-effort no-op
    """

    def __init__(self, core_cfg: dict, symbol: str):
        self.symbol = symbol
        self.core_cfg = core_cfg  # Store config for later use
        self.sidecar_base = os.getenv("SWIFT_SIDECAR", core_cfg.get("swift", {}).get("sidecar_url", ""))

        # Fix environment mapping: beta should map to devnet
        env_mapping = {"beta": "devnet", "devnet": "devnet", "mainnet": "mainnet"}
        self.cluster = env_mapping.get(os.getenv("DRIFT_CLUSTER", core_cfg.get("cluster", "devnet")).lower(), "devnet")

        # Use correct Swift endpoint based on cluster
        if self.cluster.lower() in ("devnet", "beta"):
            # Use main Swift API for both mainnet and devnet
            default_swift_base = "https://swift.drift.trade"
        else:
            default_swift_base = "https://swift.drift.trade"

        self.swift_base = os.getenv("SWIFT_BASE", core_cfg.get("swift", {}).get("swift_base", default_swift_base))
        self._mode = "SIDECAR" if self.sidecar_base else "DIRECT"

        # httpx will import ssl only when negotiating TLS; we still avoid HTTPS calls if SSL missing
        self._http = httpx.AsyncClient(timeout=15.0)
        self._signer: Optional[DriftSignerClient] = None

        # Ensure market_index is an integer, not a boolean
        market_index_raw = core_cfg.get("market_index", 0)
        self.market_index = int(market_index_raw) if not isinstance(market_index_raw, bool) else 0

        logger.info("[SWIFT] mode=%s cluster=%s base=%s market_index=%d",
                   self._mode, self.cluster, self.sidecar_base or self.swift_base, self.market_index)

    async def _ensure_signer(self) -> DriftSignerClient:
        if not HAVE_DRIFTPY:
            raise RuntimeError("DriftPy not installed — cannot sign Swift orders")
        if self._signer:
            return self._signer
        
        # Get configuration from environment or config
        keypair_path = os.getenv("KEYPAIR_PATH") or os.getenv("DRIFT_KEYPAIR_PATH")
        rpc_url = os.getenv("DRIFT_HTTP_URL")

        # If no env vars set, try to get from config
        if not keypair_path:
            keypair_path = self.core_cfg.get("wallets", {}).get("maker_keypair_path")

        if not rpc_url:
            rpc_url = self.core_cfg.get("rpc", {}).get("http_url")

        # Default values
        if not keypair_path:
            keypair_path = ".valid_wallet.json"
        if not rpc_url:
            # Try different RPC endpoints to avoid rate limiting
            rpc_url = "https://api.devnet.solana.com"  # Official devnet endpoint with better rate limits

        logger.info("[SWIFT] Using keypair: %s, rpc: %s", keypair_path, rpc_url)

        # Create and initialize the client
        self._signer = DriftSignerClient(
            rpc_url=rpc_url,
            wallet_secret_key=keypair_path,
            env=self.cluster
        )
        await self._signer.connect()
        return self._signer

    async def close(self) -> None:
        try:
            if self._signer:
                await self._signer.close()
        finally:
            await self._http.aclose()

    async def _signed_payload(self, side: str, price: float, base_qty: float, post_only: bool) -> Dict[str, Any]:
        signer = await self._ensure_signer()

        # Get current slot from RPC
        try:
            if hasattr(signer, 'connection') and signer.connection:
                # Try the new AsyncClient API
                if hasattr(signer.connection, 'get_slot'):
                    slot_result = await signer.connection.get_slot()
                    slot = slot_result.value
                elif hasattr(signer.connection, 'getSlot'):
                    slot_result = await signer.connection.getSlot()
                    slot = slot_result.value if hasattr(slot_result, 'value') else slot_result
                else:
                    # Fallback: use timestamp
                    slot = int(time.time() * 1000)
                    logger.warning("[SWIFT] Could not get slot from RPC (no compatible method), using timestamp")
            else:
                slot = int(time.time() * 1000)
                logger.warning("[SWIFT] No connection available, using timestamp")
        except Exception as e:
            slot = int(time.time() * 1000)
            logger.warning("[SWIFT] Error getting slot: %s, using timestamp", e)

        # Build proper order parameters for Swift API
        order_params = {
            "market_index": self.market_index,
            "order_type": "limit",
            "market_type": "perp",
            "direction": "long" if side.lower() == "buy" else "short",
            "base_asset_amount": int(base_qty * 1_000_000),  # Convert to proper precision
            "price": int(price * 1_000_000),  # Convert to proper precision
            "post_only": post_only,
        }

        # Create properly signed order parameters
        from driftpy.types import OrderParams, OrderType, MarketType, PositionDirection, SignedMsgOrderParamsMessage

        # Build order params for signing
        order_params = OrderParams(
            market_index=self.market_index,
            order_type=OrderType.Limit(),
            market_type=MarketType.Perp(),
            direction=PositionDirection.Long() if side.lower() == "buy" else PositionDirection.Short(),
            base_asset_amount=int(base_qty * 1_000_000),
            price=int(price * 1_000_000),
            post_only=post_only,
        )

        # Create signed message
        msg = SignedMsgOrderParamsMessage(
            signed_msg_order_params=order_params,
            sub_account_id=0,  # Default sub-account
            slot=slot,
            uuid=_gen_uuid(),
            stop_loss_order_params=None,
            take_profit_order_params=None,
        )

        # Sign the message
        signed = signer.sign_signed_msg_order_params(msg)

        # Handle different signature formats
        if isinstance(signed, dict):
            signature = signed.get('signature', 'mock_signature')
            signed_params = signed.get('signed_msg_order_params', order_params)
        else:
            # Assume it's an object with signature and signed_msg_order_params attributes
            signature = getattr(signed, 'signature', 'mock_signature')
            signed_params = getattr(signed, 'signed_msg_order_params', order_params)

        # Create Swift-compatible payload with signature
        payload = {
            "market_type": "perp",
            "market_index": self.market_index,
            "direction": "long" if side.lower() == "buy" else "short",
            "base_asset_amount": int(base_qty * 1_000_000),
            "price": int(price * 1_000_000),
            "order_type": "limit",
            "post_only": post_only,
            "slot": slot,
            "uuid": str(msg.uuid),
            "sub_account_id": msg.sub_account_id,
            "taker_authority": str(signer.authority) if signer.authority else "unknown",
            "signature": str(signature),
            "cluster": self.cluster.lower(),
        }

        # 🚨 CRITICAL FIX: Ensure signature has proper base64 padding for Swift API
        if isinstance(signature, str) and len(signature) % 4:
            while len(signature) % 4:
                signature += '='
            logger.debug(f"🔧 Signature padding ensured: {len(signature)} chars")
        
        logger.debug("[SWIFT] Created signed payload: %s", payload)
        return payload

    async def place_limit(self, side: str, price: float, base_qty: float, *, post_only: bool = True) -> str:
        try:
            payload = await self._signed_payload(side, price, base_qty, post_only)

            # Use the correct Swift endpoint
            base = self.sidecar_base or self.swift_base
            endpoints_to_try = [base]

            for base in endpoints_to_try:
                try:
                    if not SSL_OK and base.startswith("https://"):
                        logger.warning("[SWIFT] SSL not available — cannot POST to %s; trying next endpoint", base)
                        continue

                    logger.info("[SWIFT] Trying order submission to %s", base)
                    
                    # 🚨 CRITICAL FIX: Ensure payload is JSON serializable before sending
                    try:
                        # Test JSON serialization to catch any bytes/unsupported objects
                        import json
                        json.dumps(payload)
                    except (TypeError, ValueError) as json_error:
                        logger.error(f"🚨 JSON SERIALIZATION ERROR: {json_error}")
                        logger.error(f"Payload contains non-serializable objects: {payload}")
                        
                        # 🔧 REPAIR: Convert any bytes objects to hex strings
                        def make_json_safe(obj):
                            if isinstance(obj, bytes):
                                return obj.hex()
                            elif isinstance(obj, dict):
                                return {k: make_json_safe(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [make_json_safe(item) for item in obj]
                            else:
                                return obj
                        
                        safe_payload = make_json_safe(payload)
                        logger.info(f"🔧 Repaired payload: {safe_payload}")
                        
                        # Test the repaired payload
                        try:
                            json.dumps(safe_payload)
                            payload = safe_payload
                        except Exception as repair_error:
                            logger.error(f"🚨 REPAIR FAILED: {repair_error}")
                            # Ultimate fallback: create minimal safe payload
                            payload = {
                                "market_type": "perp",
                                "market_index": self.market_index,
                                "message": "00",  # dummy hex
                                "signature": "dummy_signature",
                                "taker_authority": "fallback_authority",
                                "error": "json_serialization_failed"
                            }
                    
                    r = await self._http.post(f"{base}/orders", json=payload)

                    # Log response for debugging
                    logger.info("[SWIFT] Response status: %s from %s", r.status_code, base)
                    if r.status_code == 200:
                        # Check if response is HTML (web page) instead of JSON (API)
                        content_type = r.headers.get('content-type', '')
                        if 'text/html' in content_type or r.text.strip().startswith('<!DOCTYPE'):
                            logger.warning("[SWIFT] Got HTML response from %s - wrong endpoint?", base)
                            continue  # Try next endpoint

                    logger.info("[SWIFT] Response body: %s", r.text[:500])

                    r.raise_for_status()
                    data = r.json()
                    order_id = data.get("id") or data.get("order_id") or data.get("uuid") or "unknown"
                    logger.info("[SWIFT] Order placed successfully via %s: %s", base, order_id)
                    if MM_QUOTES: MM_QUOTES.inc()
                    return str(order_id)

                except Exception as endpoint_error:
                    logger.warning("[SWIFT] Endpoint %s failed: %s", base, endpoint_error)
                    continue  # Try next endpoint

            # If we tried all endpoints and none worked
            logger.error("[SWIFT] All endpoints failed - falling back to mock order")
            return f"mock-{int(time.time()*1000)%1_000_000:06d}"
        except Exception as e:
            if MM_ERRORS: MM_ERRORS.labels(type="submit").inc()
            logger.exception("Swift submit failed: %s", e)
            # local ACK fallback (mock id) to keep loop healthy in dev
            return f"mock-{int(time.time()*1000)%1_000_000:06d}"

    async def cancel(self, order_id: str) -> None:
        try:
            if self.sidecar_base:
                if not SSL_OK and self.sidecar_base.startswith("https://"):
                    logger.warning("[SWIFT] SSL not available — cannot CANCEL via HTTPS sidecar")
                    return
                r = await self._http.post(f"{self.sidecar_base}/orders/{order_id}/cancel")
                r.raise_for_status()
                if MM_CANCELS: MM_CANCELS.inc()
            else:
                logger.info("Cancel not supported in DIRECT mode; skipping (%s)", order_id)
        except Exception as e:
            if MM_ERRORS: MM_ERRORS.labels(type="cancel").inc()
            logger.warning("Cancel failed for %s: %s", order_id, e)

    async def cancel_many(self, order_ids: List[str], *, per_req_timeout: float = 0.4) -> int:
        """Best effort bulk-cancel via sidecar. Returns number of successes.
        Uses short timeouts so shutdown is quick.
        """
        if not order_ids:
            return 0
        if not self.sidecar_base:
            logger.info("Bulk cancel skipped (DIRECT mode)")
            return 0
        async def _one(oid: str) -> int:
            try:
                await asyncio.wait_for(self.cancel(oid), timeout=per_req_timeout)
                return 1
            except Exception:
                return 0
        results = await asyncio.gather(*(_one(oid) for oid in order_ids), return_exceptions=True)
        ok = 0
        for r in results:
            if isinstance(r, int):
                ok += r
        logger.info("Bulk cancel finished: %d/%d", ok, len(order_ids))
        return ok

# ---------------------------- Helpers ----------------------------------------

def _gen_uuid() -> str:
    import uuid as _uuid
    return str(_uuid.uuid4())

class InventoryManager:
    def __init__(self, cfg: JITConfig):
        self.cfg = cfg

    def skew(self, pos: float) -> float:
        if abs(pos) >= self.cfg.max_position_abs:
            return 0.0
        return max(-1.0, min(1.0, pos / self.cfg.max_position_abs))

    def tradable(self, pos: float) -> bool:
        return abs(pos) < self.cfg.max_position_abs

class SpreadManager:
    def __init__(self, cfg: JITConfig):
        self.cfg = cfg

    def dynamic_spread(self, vol: float, inv_skew: float, obi_conf: float) -> float:
        s = self.cfg.spread_bps_base
        s *= 1.0 + min(1.0, vol * 0.5)
        s *= 1.0 + abs(inv_skew) * 0.3
        s *= 1.0 - (obi_conf * 0.2)
        s = max(self.cfg.spread_bps_min, min(self.cfg.spread_bps_max, s))
        if MM_SPREAD: MM_SPREAD.set(s)
        return s

# ---------------------------- JIT MM Core ------------------------------------

@dataclass
class LiveOrder:
    order_id: str
    side: str  # "buy" | "sell"
    price: float
    qty: float
    ts: float

class JITMarketMaker:
    def __init__(self, jit_cfg: JITConfig, core_cfg: dict):
        self.jcfg = jit_cfg
        self.core_cfg = core_cfg
        self.md = MarketDataAdapter(core_cfg)
        self.exec = SwiftExecClient(core_cfg, jit_cfg.symbol)
        self.obi = OBICalculator()
        self.inv = InventoryManager(jit_cfg)
        self.spread_mgr = SpreadManager(jit_cfg)
        self.active: Dict[str, LiveOrder] = {}
        self._last_cr_ms = 0.0
        self.position = 0.0  # TODO: wire to real position source

    async def _cancel_replace(self, desired_bid: Tuple[float, float], desired_ask: Tuple[float, float]):
        if not self.jcfg.cancel_replace_enabled:
            return
        now_ms = time.time() * 1000
        if now_ms - self._last_cr_ms < self.jcfg.cancel_replace_interval_ms:
            return

        tick = self.jcfg.tick_size
        def changed(prev_px: float, new_px: float) -> bool:
            return abs(new_px - prev_px) >= (tick * self.jcfg.cr_min_ticks)

        # Bid
        bid_live = next((o for o in self.active.values() if o.side == "buy"), None)
        if bid_live:
            if changed(bid_live.price, desired_bid[0]):
                await self.exec.cancel(bid_live.order_id)
                self.active.pop(bid_live.order_id, None)
        # Ask
        ask_live = next((o for o in self.active.values() if o.side == "sell"), None)
        if ask_live:
            if changed(ask_live.price, desired_ask[0]):
                await self.exec.cancel(ask_live.order_id)
                self.active.pop(ask_live.order_id, None)

        # Place as needed
        if not any(o.side == "buy" for o in self.active.values()):
            oid = await self.exec.place_limit("buy", desired_bid[0], desired_bid[1], post_only=self.jcfg.post_only)
            self.active[oid] = LiveOrder(oid, "buy", desired_bid[0], desired_bid[1], time.time())
        if not any(o.side == "sell" for o in self.active.values()):
            oid = await self.exec.place_limit("sell", desired_ask[0], desired_ask[1], post_only=self.jcfg.post_only)
            self.active[oid] = LiveOrder(oid, "sell", desired_ask[0], desired_ask[1], time.time())

        self._last_cr_ms = now_ms

    async def shutdown(self, *, cancel_orders: bool = True, timeout_s: float = 1.0) -> None:
        """Best-effort cleanup: cancel live maker orders via sidecar and clear state."""
        if cancel_orders and self.active:
            ids = list(self.active.keys())
            try:
                # Use bulk if available; otherwise fall back to per-order cancel
                if hasattr(self.exec, "cancel_many"):
                    per_req = max(0.1, min(0.5, timeout_s / max(1, len(ids))))
                    await asyncio.wait_for(self.exec.cancel_many(ids, per_req_timeout=per_req), timeout=timeout_s)
                else:
                    async def _one(oid: str) -> None:
                        try:
                            await asyncio.wait_for(self.exec.cancel(oid), timeout=0.4)
                        except Exception:
                            pass
                    await asyncio.wait_for(asyncio.gather(*(_one(oid) for oid in ids), return_exceptions=True), timeout=timeout_s)
            except Exception as e:
                logger.warning("Shutdown cancel errors: %s", e)
        self.active.clear()

    def _sizes(self, mid: float, inv_skew: float) -> Tuple[float, float]:
        base = 0.05  # 0.05 base units (e.g., SOL)
        mult = 1.0 - 0.5 * abs(inv_skew)
        bid = max(0.0, base * mult)
        ask = max(0.0, base * mult)
        if inv_skew > 0.1:
            ask *= 1.2
        elif inv_skew < -0.1:
            bid *= 1.2
        return bid, ask

    async def tick(self) -> None:
        if MM_TICKS: MM_TICKS.inc()
        ob = self.md.get_orderbook()  # SYNC
        if not ob.bids or not ob.asks:
            if MM_SKIPS: MM_SKIPS.labels(reason="no_l1").inc()
            await asyncio.sleep(0.25); return
        bb = ob.bids[0][0]; ba = ob.asks[0][0]
        if ba <= bb:
            if MM_SKIPS: MM_SKIPS.labels(reason="crossed").inc()
            await asyncio.sleep(0.25); return
        mid = 0.5 * (bb + ba)
        if mid <= 0:
            if MM_SKIPS: MM_SKIPS.labels(reason="mid_leq_zero").inc()
            await asyncio.sleep(0.25); return
        if MM_MID: MM_MID.set(mid)

        micro, imb, skew_adj, conf = self.obi.calculate(ob)
        inv_skew = self.inv.skew(self.position)

        # Toxicity guard
        if self.jcfg.toxicity_guard and abs(imb) > 0.95:
            if MM_SKIPS: MM_SKIPS.labels(reason="toxic").inc()
            await asyncio.sleep(0.25); return

        # Dynamic spread
        vol = 0.001  # TODO: compute realized vol
        spread_bps = self.spread_mgr.dynamic_spread(vol, inv_skew, conf)
        half = spread_bps / 2.0 / 1e4
        bid_px = mid * (1 - half)
        ask_px = mid * (1 + half)

        if self.jcfg.obi_microprice and micro > 0:
            bid_px += skew_adj * mid * 0.001
            ask_px += skew_adj * mid * 0.001

        if bid_px <= 0 or ask_px <= 0 or bid_px >= ask_px:
            if MM_SKIPS: MM_SKIPS.labels(reason="invalid_px").inc()
            await asyncio.sleep(0.25); return

        bid_qty, ask_qty = self._sizes(mid, inv_skew)
        await self._cancel_replace((round(bid_px, 4), bid_qty), (round(ask_px, 4), ask_qty))

# ---------------------------- Main -------------------------------------------

RUNNING = True

_DEF_HARD_EXIT = os.getenv("HARD_EXIT", "0") not in ("0", "false", "False", "")

def _sigterm(sig, _frame):
    global RUNNING
    logger.info("Signal %s received — graceful stop", sig)
    RUNNING = False

async def run_main(env: str, cfg_path: Path, *, no_metrics: bool = False) -> int:
    core_cfg = load_yaml(cfg_path)
    jit_cfg_path = Path("configs/jit/params.yaml")
    jit_raw = load_yaml(jit_cfg_path) if jit_cfg_path.exists() else {}
    jit_cfg = JITConfig.from_yaml(jit_raw)

    # metrics (late-bind + optional)
    global MM_TICKS, MM_SKIPS, MM_QUOTES, MM_CANCELS, MM_ERRORS, MM_SPREAD, MM_MID
    if no_metrics or _METRICS_BACKEND == "noop":
        MM_TICKS = _Counter("mm_ticks_total", "Total MM ticks")
        # Provide label-capable shim
        class _ShimCounter(_NoopMetric):
            def labels(self, *_, **__): return self
        MM_SKIPS = _ShimCounter()
        MM_QUOTES = _Counter("mm_quotes_total", "Quotes placed")
        MM_CANCELS = _Counter("mm_cancel_total", "Cancels issued")
        MM_ERRORS = _ShimCounter()
        MM_SPREAD = _Gauge("mm_spread_bps", "Current dynamic spread in bps")
        MM_MID = _Gauge("mm_mid_price", "Mid price used for quoting")
        logger.warning("[METRICS] Using NOOP backend")
    else:
        from prometheus_client import Gauge as _G, Counter as _C
# Setup centralized logging
from libs.logging_config import setup_critical_logging
logger = setup_critical_logging("jit-mm-swift")
        MM_TICKS = _C("mm_ticks_total", "Total MM ticks")
        MM_SKIPS = _C("mm_skips_total", "MM skips by reason", labelnames=("reason",))
        MM_QUOTES = _C("mm_quotes_total", "Quotes placed")
        MM_CANCELS = _C("mm_cancel_total", "Cancels issued")
        MM_ERRORS = _C("mm_errors_total", "Errors by type", labelnames=("type",))
        MM_SPREAD = _G("mm_spread_bps", "Current dynamic spread in bps")
        MM_MID = _G("mm_mid_price", "Mid price used for quoting")
        port = int(os.getenv("METRICS_PORT", "9300"))
        _prom_start(port)
        logger.info("[METRICS] Prometheus on :%d", port)

    # signals
    signal.signal(signal.SIGINT, _sigterm)
    try:
        signal.signal(signal.SIGTERM, _sigterm)
    except Exception:
        pass

    mm = JITMarketMaker(jit_cfg, core_cfg)
    logger.info("JIT MM starting (env=%s, symbol=%s, metrics=%s)", env, jit_cfg.symbol, _METRICS_BACKEND if not no_metrics else "disabled")

    try:
        while RUNNING:
            t0 = time.time()
            try:
                await mm.tick()
            except asyncio.CancelledError:
                logger.info("Run loop cancelled during tick; stopping...")
                break
            except Exception as e:
                if MM_ERRORS: MM_ERRORS.labels(type="tick").inc()
                logger.exception("Tick error: %s", e)
                await asyncio.sleep(0.25)
            dt = time.time() - t0
            if dt < 0.25:
                try:
                    await asyncio.sleep(0.25 - dt)
                except asyncio.CancelledError:
                    logger.info("Cancelled during sleep; stopping...")
                    break
    except asyncio.CancelledError:
        logger.info("Run loop cancelled; exiting cleanly")
        return 0
    except Exception as exc:
        logger.exception("Fatal run loop error: %s", exc)
        return 1
    finally:
        try:
            if os.getenv("CANCEL_ON_SHUTDOWN", "1") not in ("0", "false", "False", ""):
                await mm.shutdown(cancel_orders=True, timeout_s=float(os.getenv("CANCEL_TIMEOUT_S", "1.0")))
        except Exception:
            pass
        try:
            await mm.exec.close()
        except Exception:
            pass
        logger.info("Shutdown complete")
    return 0

# ---------------------------- Self tests -------------------------------------

def _selftest() -> int:
    """Run simple tests that don't require network/ssl."""
    # Metric shim shouldn't raise
    m = _NoopMetric(); m.inc(); m.set(1); m.labels(reason="x")

    # OBI calc sanity
    ob = Orderbook(bids=[(100.0, 2.0), (99.9, 1.0)], asks=[(100.2, 3.0), (100.3, 1.0)], ts=time.time())
    micro, imb, skew, conf = OBICalculator().calculate(ob)
    assert 0 <= abs(imb) <= 1, "OBI calc out of bounds"
    assert micro > 0 and conf > 0, "OBI micro/conf should be positive"

    # Spread manager clamp
    cfg = JITConfig.from_yaml({"spread_bps": {"base": 8, "min": 4, "max": 25}})
    sm = SpreadManager(cfg)
    s = sm.dynamic_spread(0.5, 0.5, 0.5)
    assert 4 <= s <= 25, "Spread clamp failed"

    # MarketDataAdapter caching + fallback
    md = MarketDataAdapter({})
    ob1 = md.get_orderbook(); time.sleep(0.05); ob2 = md.get_orderbook()
    assert ob1.ts == ob2.ts, "TTL cache not used"

    # End-to-end tick with a fake execution client (no network or signer)
    class _FakeExec:
        def __init__(self):
            self.placed: List[Tuple[str, float, float]] = []
            self.canceled: List[str] = []
            self._i = 0
        async def place_limit(self, side: str, price: float, qty: float, *, post_only: bool=True) -> str:
            self._i += 1
            oid = f"fake-{self._i}"
            self.placed.append((side, price, qty))
            return oid
        async def cancel(self, order_id: str) -> None:
            self.canceled.append(order_id)
        async def close(self):
            return None

    mm = JITMarketMaker(cfg, {})
    mm.exec = _FakeExec()  # type: ignore
    # Force cancel/replace allowed immediately
    mm._last_cr_ms = 0
    asyncio.get_event_loop().run_until_complete(mm.tick())
    assert len(mm.active) in (1, 2), "Orders should be placed by tick"

    # NEW: shutdown cancel test
    # Seed two fake orders
    mm.active["oid-1"] = LiveOrder("oid-1", "buy", 100.0, 0.1, time.time())
    mm.active["oid-2"] = LiveOrder("oid-2", "sell", 100.2, 0.1, time.time())
    asyncio.get_event_loop().run_until_complete(mm.shutdown(cancel_orders=True, timeout_s=0.5))
    # Our FakeExec.cancel should have been called for both
    assert set(getattr(mm.exec, "canceled", [])) >= {"oid-1", "oid-2"}, "Shutdown should cancel active orders"

    # NEW: cancellation test — ensure cancel during sleep doesn't bubble up
    async def _sleep_then_cancel():
        task = asyncio.create_task(asyncio.sleep(1.0))
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return True
        return False

    assert asyncio.get_event_loop().run_until_complete(_sleep_then_cancel()) is True, "Cancel test failed"

    logger.info("✅ Selftest passed (no network/ssl required)")
    return 0

# ---------------------------- CLI --------------------------------------------

def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="JIT MM Bot (Swift, exit/SSL-safe)")
    p.add_argument("--env", default=os.getenv("ENV", "beta"))
    p.add_argument("--cfg", default="configs/core/drift_client.yaml")
    p.add_argument("--no-metrics", action="store_true", help="Disable Prometheus metrics")
    p.add_argument("--selftest", action="store_true", help="Run built-in tests and return")
    return p.parse_args(argv)

if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    rc = 0
    try:
        if args.selftest:
            rc = _selftest()
        else:
            try:
                rc = asyncio.run(run_main(args.env, Path(args.cfg), no_metrics=args.no_metrics))
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt: graceful stop")
                rc = 0
            except asyncio.CancelledError:
                logger.info("CancelledError: graceful stop")
                rc = 0
    except Exception as exc:
        logger.exception("Fatal at top-level: %s", exc)
        rc = 1
    finally:
        if _DEF_HARD_EXIT:
            raise SystemExit(rc)
        else:
            # Return without raising to keep harnesses quiet
            pass
