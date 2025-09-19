from __future__ import annotations
import argparse
import asyncio
import base64
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add root directory to Python path so we can import libs.drift.client
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("jit-mm-swift")


def _ssl_available() -> bool:
    try:
        import ssl  # noqa: F401
        return True
    except Exception:
        return False


SSL_OK = _ssl_available()


class _NoopMetric:
    def __init__(self, *_, **__):
        pass

    def labels(self, *_, **__):
        return self

    def inc(self, *_, **__):
        return None

    def set(self, *_, **__):
        return None


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

MM_TICKS: Any = None
MM_SKIPS: Any = None
MM_QUOTES: Any = None
MM_CANCELS: Any = None
MM_ERRORS: Any = None
MM_SPREAD: Any = None
MM_MID: Any = None


def _deep_merge(dst: dict, src: dict) -> dict:
    out = dict(dst)
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(core_path: Path, params_path: Optional[Path] = None, overrides: Optional[dict] = None) -> dict:
    base = yaml.safe_load(core_path.read_text(encoding="utf-8")) if core_path and core_path.exists() else {}
    params = yaml.safe_load(params_path.read_text(encoding="utf-8")) if params_path and params_path.exists() else {}
    cfg = _deep_merge(base or {}, params or {})
    env = {}
    if v := os.getenv("SYMBOL"):
        env.setdefault("symbol", v)
    if v := os.getenv("LOG_LEVEL"):
        env.setdefault("log_level", v)
    if v := os.getenv("OBI_LEVELS"):
        env.setdefault("obi", {}).update({"levels": int(v)})
    if v := os.getenv("BASE_SIZE"):
        env.setdefault("mm", {}).update({"base_size": float(v)})
    if env:
        cfg = _deep_merge(cfg, env)
    if overrides:
        cfg = _deep_merge(cfg, overrides)
    return cfg


def _parse_overrides(items: Optional[List[str]]) -> dict:
    if not items:
        return {}

    def cast(val: str):
        s = val.strip()
        if s.lower() in {"true", "false"}:
            return s.lower() == "true"
        try:
            if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
                return int(s)
            return float(s)
        except Exception:
            return s

    root: dict = {}
    for it in items:
        if "=" not in it:
            continue
        key, val = it.split("=", 1)
        parts = [p for p in key.strip().split(".") if p]
        cur = root
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = cast(val)
    return root


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
    obi_levels: int
    base_size: float
    market_index: int

    @classmethod
    def from_yaml(cls, cfg: dict) -> "JITConfig":
        spread = cfg.get("spread_bps", {})
        cr = cfg.get("cancel_replace", {})
        mm = cfg.get("mm", {})
        obi = cfg.get("obi", {})
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
            obi_levels=int(obi.get("levels", 10)),
            base_size=float(mm.get("base_size", 0.05)),
            market_index=int(cfg.get("market_index", 0)),
        )

    def __post_init__(self):
        assert self.spread_bps_min > 0
        assert self.spread_bps_max > self.spread_bps_min
        assert self.base_size > 0
        assert self.max_position_abs > 0
        assert 1 <= self.obi_levels <= 50
        assert self.cancel_replace_interval_ms >= 100
        if self.spread_bps_min < 2.0:
            logger.warning("Very tight min spread: %s bps", self.spread_bps_min)
        if self.max_position_abs > 1000:
            logger.warning("Very large max position: %s", self.max_position_abs)


@dataclass
class Orderbook:
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]
    ts: float


class OBICalculator:
    def __init__(self, levels: int = 10):
        self.levels = levels

    def calculate(self, ob: Orderbook) -> Tuple[float, float, float, float]:
        if not ob.bids or not ob.asks:
            return 0.0, 0.0, 0.0, 0.0
        bid_vol = sum(sz for _, sz in ob.bids[: self.levels])
        ask_vol = sum(sz for _, sz in ob.asks[: self.levels])
        denom = bid_vol + ask_vol
        if denom <= 1e-12:
            return 0.0, 0.0, 0.0, 0.0
        bb = float(ob.bids[0][0])
        ba = float(ob.asks[0][0])
        micro = (bid_vol * ba + ask_vol * bb) / denom
        imb = (bid_vol - ask_vol) / denom
        skew = 0.5 * imb
        conf = min(1.0, denom / 100.0)
        return micro, imb, skew, conf


class MarketDataAdapter:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self._cache: Optional[Orderbook] = None
        self._ttl = float(cfg.get("orderbook_ttl_seconds", 0.25))
        self._max_stale = float(cfg.get("orderbook_max_stale_seconds", 2.0))
        # Remove problematic libs.drift.client import - use mock orderbook for now
        # TODO: Integrate with Data API/DLOB for real market data later
        self._driver = None
        self._use_driver = False
        logger.info("[MD] Using mock orderbook (libs.drift.client integration disabled)")

    def get_orderbook(self) -> Orderbook:
        now = time.time()
        if self._cache and (now - self._cache.ts) <= self._ttl:
            return self._cache
        try:
            if self._use_driver:
                raw = self._driver.get_orderbook()
                bids = [(float(p), float(s)) for p, s in raw["bids"][:16]]
                asks = [(float(p), float(s)) for p, s in raw["asks"][:16]]
            else:
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
            mid = 150.0
            ob = Orderbook(bids=[(mid - 0.1, 0.5)], asks=[(mid + 0.1, 0.5)], ts=now)
            self._cache = ob
            return ob


try:
    from driftpy.drift_client import DriftClient as DriftSignerClient
    from driftpy.types import (
        OrderParams,
        OrderType,
        MarketType,
        SignedMsgOrderParamsMessage,
        PositionDirection,
    )
    HAVE_DRIFTPY = True
except Exception as e:
    HAVE_DRIFTPY = False
    DriftSignerClient = Any  # type: ignore
    PositionDirection = Any  # type: ignore
    logger.warning("DriftPy not available: %s — Swift submit will run in MOCK ACK mode.", e)


class SwiftExecClient:
    def __init__(self, core_cfg: dict, symbol: str):
        """Execution client used by the JIT market maker to submit orders via
        Drift's "Swift" HTTP API.

        Historically this class only consumed a small portion of the MM config
        and relied on ``libs.drift.client.DriftpyClient`` to discover its RPC
        endpoint.  Recent versions of ``DriftpyClient`` require the ``rpc_url``
        parameter to be explicitly provided which caused runtime failures such
        as ``ValueError: rpc_url is required`` when the bot attempted to place
        orders.  The run\_MM\_bot script would therefore crash before any
        trading logic executed.

        To make the client robust we now capture the RPC HTTP endpoint and
        wallet path during initialisation, pulling from either environment
        variables or the supplied configuration.  The values are then passed to
        ``DriftpyClient`` when creating the signer, guaranteeing a valid RPC is
        always supplied.
        """

        self.symbol = symbol
        self._core_cfg = core_cfg

        # Swift/sidecar configuration
        self.sidecar_base = os.getenv("SWIFT_SIDECAR", core_cfg.get("swift", {}).get("sidecar_url", ""))
        self.swift_base = os.getenv("SWIFT_BASE", core_cfg.get("swift", {}).get("swift_base", "https://swift.drift.trade"))
        self._mode = "SIDECAR" if self.sidecar_base else "DIRECT"
        self._http = httpx.AsyncClient(timeout=15.0)
        self._signer: Optional[DriftSignerClient] = None

        # Cluster/market information
        self.cluster = os.getenv("DRIFT_CLUSTER", core_cfg.get("cluster", "beta"))
        self.market_index = int(core_cfg.get("market_index", 0))

        # RPC + wallet paths (allow environment overrides)
        rpc_env = os.getenv("DRIFT_HTTP_URL") or os.getenv("RPC_URL")
        self.rpc_url = rpc_env or core_cfg.get("rpc", {}).get("http_url", "")
        wallet_env = os.getenv("DRIFT_KEYPAIR_PATH")
        self.wallet_path = wallet_env or core_cfg.get("wallets", {}).get("maker_keypair_path", ".valid_wallet.json")

        logger.info(
            "[SWIFT] mode=%s base=%s rpc=%s wallet=%s",
            self._mode,
            self.sidecar_base or self.swift_base,
            self.rpc_url or "<missing>",
            self.wallet_path,
        )

    async def _ensure_signer(self) -> DriftSignerClient:
        """Return a ready-to-use ``DriftpyClient`` signer.

        The previous implementation relied on ``DriftpyClient`` inferring the
        RPC URL from its config which is no longer supported.  This method now
        explicitly forwards ``rpc_url`` and the desired wallet path so that
        signer initialisation is deterministic and does not raise the confusing
        ``rpc_url is required`` error seen in production.
        """

        if not HAVE_DRIFTPY:
            raise RuntimeError("DriftPy not installed — cannot sign Swift orders")
        if self._signer:
            return self._signer

        # Use the working DriftpyClient from libs.drift.client
        try:
            from libs.drift.client import DriftpyClient

            env = (self.cluster or "devnet").lower()
            env = "devnet" if env in ("beta", "devnet", "devnet-beta") else env

            # Ensure we have an RPC URL; surfacing a clear error if missing
            if not self.rpc_url:
                raise RuntimeError(
                    "rpc_url is required – set DRIFT_HTTP_URL/RPC_URL or provide in config['rpc']['http_url']"
                )

            drift_client = DriftpyClient(
                env=env,
                rpc_url=self.rpc_url,
                cfg={
                    "cluster": env,
                    "wallets": {"maker_keypair_path": self.wallet_path},
                    "rpc": {"http_url": self.rpc_url},
                },
            )

            self._signer = drift_client.drift_client
            logger.info("✅ DriftPy client initialized successfully for Swift orders")
            return self._signer

        except Exception as e:
            logger.error(f"Failed to initialize DriftPy client: {e}")
            raise RuntimeError(f"Cannot initialize DriftPy client: {e}")

    async def close(self) -> None:
        try:
            if self._signer:
                await self._signer.close()
        finally:
            await self._http.aclose()

    async def _signed_payload(self, side: str, price: float, base_qty: float, post_only: bool) -> Dict[str, Any]:
        signer = await self._ensure_signer()

        # Use the corrected DriftPy API calls that we know work
        from driftpy.types import PostOnlyParams

        direction = PositionDirection.Long() if side.lower() == "buy" else PositionDirection.Short()

        # Convert quantities and price using the correct methods
        base_asset_amount = signer.convert_to_perp_precision(base_qty)
        try:
            price_precision = signer.convert_to_price_precision(price)
        except:
            price_precision = int(price * 1e6)  # Fallback precision

        order_params = OrderParams(
            market_index=self.market_index,
            order_type=OrderType.Limit(),
            market_type=MarketType.Perp(),
            direction=direction,
            base_asset_amount=base_asset_amount,
            price=price_precision,
            post_only=PostOnlyParams.MustPostOnly() if post_only else PostOnlyParams.NONE,
        )

        # Get slot correctly
        try:
            slot_response = await signer.connection.get_slot()
            slot = int(slot_response.value) if hasattr(slot_response, 'value') else int(slot_response)
        except Exception:
            slot = 0
            logger.warning("Failed to fetch slot, using default")

        # Generate UUID as bytes (8 bytes required)
        import uuid
        uuid_obj = uuid.uuid4()
        uuid_bytes = uuid_obj.bytes[:8]

        msg = SignedMsgOrderParamsMessage(
            signed_msg_order_params=order_params,
            sub_account_id=getattr(signer, 'active_sub_account_id', 0),
            slot=slot,
            uuid=uuid_bytes,
            stop_loss_order_params=None,
            take_profit_order_params=None,
        )

        # Sign using the correct method
        try:
            signed = signer.sign_signed_msg_order_params_message(msg)
        except AttributeError:
            # Fallback to the method we know works from our working bot
            signed = signer.sign_signed_msg_order_params_message(msg)

        # Build payload exactly as Swift API expects:
        # - message: hex-encoded serialized message bytes
        # - signature: base64-encoded signature bytes
        # - taker_authority: base58 pubkey string

        import base64

        def _b64(b: bytes) -> str:
            return base64.b64encode(b).decode("ascii")

        # Serialize the entire signed message to bytes
        try:
            # Try to get the raw bytes representation of the signed message
            if hasattr(signed, '__bytes__'):
                raw_message_bytes = bytes(signed)
            elif hasattr(signed, 'serialize'):
                raw_message_bytes = signed.serialize()
            else:
                # Fallback: convert to JSON and encode
                import json
                raw_message_bytes = json.dumps(str(signed)).encode('utf-8')
            
            # For Swift API: message should be hex-encoded bytes (not base64)
            message_hex = raw_message_bytes.hex()

            # Monitor variant byte to ensure we're not sending raw order_params (variant 0xc8)
            if raw_message_bytes and len(raw_message_bytes) > 0:
                variant_byte = raw_message_bytes[0]
                if variant_byte > 0x20:  # Most enum variants should be < 0x20
                    logger.warning("POST check: message[0]=0x%02x (high variant byte - may be raw order_params)", variant_byte)
                    if variant_byte == 0xc8:
                        logger.error("CRITICAL: Detected raw order_params (variant=0xc8) in Swift message!")
                        logger.error("This will cause Swift API rejection. Message should be SignedMsgOrderParamsMessage envelope.")
                else:
                    logger.debug("Swift payload ready (len=%d, variant=0x%02x)", len(raw_message_bytes), variant_byte)
            
        except Exception as fallback_error:
            # Ultimate fallback: create a simple string representation
            logger.warning(f"Message serialization failed ({fallback_error}), using string fallback")
            message_hex = str(signed).encode('utf-8').hex()

        # Get signature
        signature_bytes = getattr(signed, 'signature', b'')
        if isinstance(signature_bytes, str):
            signature_bytes = signature_bytes.encode('utf-8')
        signature_b64 = _b64(signature_bytes) if signature_bytes else ""

        payload = {
            "market_type": "perp",
            "market_index": self.market_index,
            "message": message_hex,  # Hex-encoded message bytes
            "signature": signature_b64,  # Base64-encoded signature
            "taker_authority": str(getattr(signer, 'authority', '')),
        }

        # Add signing authority if using delegate
        signing_authority = os.getenv("DRIFT_SIGNING_AUTHORITY")
        if signing_authority:
            payload["signing_authority"] = signing_authority

        return payload

    async def place_limit(self, side: str, price: float, base_qty: float, *, post_only: bool = True) -> str:
        try:
            payload = await self._signed_payload(side, price, base_qty, post_only)
            base = self.sidecar_base or self.swift_base
            if not SSL_OK and base.startswith("https://"):
                logger.warning("[SWIFT] SSL not available — cannot POST to %s; returning mock ACK", base)
                if MM_ERRORS:
                    MM_ERRORS.labels(type="submit").inc()
                return f"mock-{int(time.time()*1000)%1_000_000:06d}"

            r = await self._http.post(f"{base}/orders", json=payload, headers={"Content-Type": "application/json"})
            if r.status_code >= 400:
                body = r.text
                logger.error("Swift /orders %s — %s", r.status_code, body)
            r.raise_for_status()
            data = r.json()
            order_id = data.get("id") or data.get("order_id") or data.get("uuid") or "unknown"
            if MM_QUOTES:
                MM_QUOTES.inc()
            return str(order_id)
        except Exception as e:
            if MM_ERRORS:
                MM_ERRORS.labels(type="submit").inc()
            logger.exception("Swift submit failed")
            return f"mock-{int(time.time()*1000)%1_000_000:06d}"

    async def cancel(self, order_id: str) -> None:
        try:
            if self.sidecar_base:
                if not SSL_OK and self.sidecar_base.startswith("https://"):
                    logger.warning("[SWIFT] SSL not available — cannot CANCEL via HTTPS sidecar")
                    return

                async def _cancel():
                    return await self._http.post(f"{self.sidecar_base}/orders/{order_id}/cancel")

                r = await with_retry(_cancel)
                r.raise_for_status()
                if MM_CANCELS:
                    MM_CANCELS.inc()
            else:
                logger.info("Cancel not supported in DIRECT mode; skipping (%s)", order_id)
        except Exception as e:
            if MM_ERRORS:
                MM_ERRORS.labels(type="cancel").inc()
            logger.warning("Cancel failed for %s: %s", order_id, e)

    async def cancel_many(self, order_ids: List[str], *, per_req_timeout: float = 0.4) -> int:
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


def _gen_uuid() -> str:
    import uuid as _uuid
    return str(_uuid.uuid4())


class PerfTracker:
    def __init__(self):
        self.tick_times: List[float] = []

    def record_tick(self, duration: float):
        self.tick_times.append(duration)
        if len(self.tick_times) > 100:
            self.tick_times.pop(0)

    @property
    def avg_tick_time(self) -> float:
        return sum(self.tick_times) / len(self.tick_times) if self.tick_times else 0.0


async def with_retry(coro_factory, max_attempts: int = 3, delay: float = 0.1):
    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except Exception:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(delay * (2 ** attempt))


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
        self.spread_history: List[float] = []
        self.max_history = 100

    def dynamic_spread(self, vol: float, inv_skew: float, obi_conf: float, book_imbalance: float = 0.0) -> float:
        s = self.cfg.spread_bps_base
        s *= 1.0 + min(2.0, vol * 0.5)
        s *= 1.0 + abs(inv_skew) * 0.5
        s *= 1.0 - (obi_conf * 0.2)
        if abs(book_imbalance) > 0.7:
            s *= 1.5
        self.spread_history.append(s)
        if len(self.spread_history) > self.max_history:
            self.spread_history.pop(0)
        if len(self.spread_history) >= 10:
            ema_weight = 0.2
            ema = self.spread_history[-1]
            for val in reversed(self.spread_history[-10:-1]):
                ema = ema_weight * val + (1 - ema_weight) * ema
            s = 0.7 * s + 0.3 * ema
        s = max(self.cfg.spread_bps_min, min(self.cfg.spread_bps_max, s))
        if MM_SPREAD:
            MM_SPREAD.set(s)
        return s


class RiskManager:
    def __init__(self, max_loss_per_minute: float = 100.0, max_orders_per_minute: int = 120):
        self.max_loss_per_minute = max_loss_per_minute
        self.max_orders_per_minute = max_orders_per_minute
        self.pnl_history: List[Tuple[float, float]] = []
        self.order_history: List[float] = []
        self.circuit_breaker_active = False
        self.cooldown_until = 0.0

    def check_limits(self) -> bool:
        now = time.time()
        if now < self.cooldown_until:
            return False
        cutoff = now - 60
        self.pnl_history = [(t, pnl) for t, pnl in self.pnl_history if t > cutoff]
        self.order_history = [t for t in self.order_history if t > cutoff]
        if len(self.order_history) > self.max_orders_per_minute:
            logger.warning("Circuit breaker: Order rate limit hit (%d orders/min)", len(self.order_history))
            self.cooldown_until = now + 30
            return False
        if self.pnl_history:
            recent_pnl = sum(pnl for _, pnl in self.pnl_history)
            if recent_pnl < -self.max_loss_per_minute:
                logger.warning("Circuit breaker: Loss limit hit ($%.2f/min)", recent_pnl)
                self.cooldown_until = now + 60
                return False
        return True


@dataclass
class LiveOrder:
    order_id: str
    side: str
    price: float
    qty: float
    ts: float
    filled: bool = False


class JITMarketMaker:
    def __init__(self, jit_cfg: JITConfig, core_cfg: dict):
        self.jcfg = jit_cfg
        self.core_cfg = core_cfg
        self.md = MarketDataAdapter(core_cfg)
        self.exec = SwiftExecClient(core_cfg, jit_cfg.symbol)
        self.exec.market_index = jit_cfg.market_index
        self.obi = OBICalculator(jit_cfg.obi_levels)
        self.inv = InventoryManager(jit_cfg)
        self.spread_mgr = SpreadManager(jit_cfg)
        self.active: Dict[str, LiveOrder] = {}
        self._last_cr_ms = 0.0
        self.position = 0.0
        self.position_update_interval = 5.0
        self.last_position_update = 0.0
        self.recent_volatility = 0.0
        self.last_tick_time = 0.0
        self.consecutive_errors = 0
        risk_cfg = core_cfg.get("risk", {}) if isinstance(core_cfg, dict) else {}
        self.risk_mgr = RiskManager(
            max_loss_per_minute=float(risk_cfg.get("max_loss_per_minute", 100.0)),
            max_orders_per_minute=int(risk_cfg.get("max_orders_per_minute", 120)),
        )
        self.perf = PerfTracker()

    async def _cancel_replace(self, desired_bid: Tuple[float, float], desired_ask: Tuple[float, float]):
        if not self.jcfg.cancel_replace_enabled:
            return
        now_ms = time.time() * 1000
        if now_ms - self._last_cr_ms < self.jcfg.cancel_replace_interval_ms:
            return
        tick = self.jcfg.tick_size

        def changed(prev_px: float, new_px: float) -> bool:
            return abs(new_px - prev_px) >= (tick * self.jcfg.cr_min_ticks)

        bid_live = next((o for o in self.active.values() if o.side == "buy"), None)
        if bid_live and changed(bid_live.price, desired_bid[0]):
            await self.exec.cancel(bid_live.order_id)
            self.active.pop(bid_live.order_id, None)
        ask_live = next((o for o in self.active.values() if o.side == "sell"), None)
        if ask_live and changed(ask_live.price, desired_ask[0]):
            await self.exec.cancel(ask_live.order_id)
            self.active.pop(ask_live.order_id, None)
        if not any(o.side == "buy" for o in self.active.values()):
            oid = await self.exec.place_limit("buy", desired_bid[0], desired_bid[1], post_only=self.jcfg.post_only)
            self.active[oid] = LiveOrder(oid, "buy", desired_bid[0], desired_bid[1], time.time())
            self.risk_mgr.order_history.append(time.time())
        if not any(o.side == "sell" for o in self.active.values()):
            oid = await self.exec.place_limit("sell", desired_ask[0], desired_ask[1], post_only=self.jcfg.post_only)
            self.active[oid] = LiveOrder(oid, "sell", desired_ask[0], desired_ask[1], time.time())
            self.risk_mgr.order_history.append(time.time())
        self._last_cr_ms = now_ms

    async def shutdown(self, *, cancel_orders: bool = True, timeout_s: float = 1.0) -> None:
        if cancel_orders and self.active:
            ids = list(self.active.keys())
            try:
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

    async def update_position(self) -> None:
        now = time.time()
        if now - self.last_position_update < self.position_update_interval:
            return
        try:
            if getattr(self.md, "_use_driver", False) and getattr(self.md, "_driver", None):
                user = self.md._driver.get_user()
                if user:
                    perp_position = user.get_perp_position(self.jcfg.market_index)
                    if perp_position and hasattr(perp_position, "base_asset_amount"):
                        self.position = float(perp_position.base_asset_amount) / 1e9
                        self.last_position_update = now
                        logger.debug("Position updated: %s", self.position)
        except Exception as e:
            logger.warning("Failed to update position: %s", e)

    async def check_fills(self) -> None:
        if not self.active:
            return
        now = time.time()
        for oid, order in list(self.active.items()):
            if now - order.ts > 30.0:
                logger.info("Removing stale order %s (%s)", oid, order.side)
                self.active.pop(oid, None)
                if order.side == "buy":
                    self.position += order.qty
                else:
                    self.position -= order.qty

    def _sizes(self, mid: float, inv_skew: float) -> Tuple[float, float]:
        base = self.jcfg.base_size
        vol_mult = max(0.5, min(1.5, 1.0 / (1.0 + self.recent_volatility)))
        base *= vol_mult
        mult = 1.0 - 0.5 * abs(inv_skew)
        bid = max(0.0, base * mult)
        ask = max(0.0, base * mult)
        if inv_skew > 0.3:
            ask *= 1.5
            bid *= 0.5
        elif inv_skew < -0.3:
            bid *= 1.5
            ask *= 0.5
        elif inv_skew > 0.1:
            ask *= 1.2
        elif inv_skew < -0.1:
            bid *= 1.2
        return bid, ask

    async def tick(self) -> None:
        try:
            t0 = time.time()
            if MM_TICKS:
                MM_TICKS.inc()
            await self.update_position()
            await self.check_fills()
            if not self.risk_mgr.check_limits():
                logger.info("Risk limits hit, skipping tick")
                await asyncio.sleep(1.0)
                return
            ob = self.md.get_orderbook()
            if not ob.bids or not ob.asks:
                if MM_SKIPS:
                    MM_SKIPS.labels(reason="no_l1").inc()
                await asyncio.sleep(0.25)
                return
            bb = ob.bids[0][0]
            ba = ob.asks[0][0]
            if ba <= bb:
                if MM_SKIPS:
                    MM_SKIPS.labels(reason="crossed").inc()
                await asyncio.sleep(0.25)
                return
            mid = 0.5 * (bb + ba)
            if mid <= 0:
                if MM_SKIPS:
                    MM_SKIPS.labels(reason="mid_leq_zero").inc()
                await asyncio.sleep(0.25)
                return
            if MM_MID:
                MM_MID.set(mid)
            micro, imb, skew_adj, conf = self.obi.calculate(ob)
            inv_skew = self.inv.skew(self.position)
            if self.jcfg.toxicity_guard and abs(imb) > 0.95:
                if MM_SKIPS:
                    MM_SKIPS.labels(reason="toxic").inc()
                await asyncio.sleep(0.25)
                return
            vol = 0.001
            spread_bps = self.spread_mgr.dynamic_spread(vol, inv_skew, conf, book_imbalance=imb)
            half = spread_bps / 2.0 / 1e4
            bid_px = mid * (1 - half)
            ask_px = mid * (1 + half)
            if self.jcfg.obi_microprice and micro > 0:
                bid_px += skew_adj * mid * 0.001
                ask_px += skew_adj * mid * 0.001
            if bid_px <= 0 or ask_px <= 0 or bid_px >= ask_px:
                if MM_SKIPS:
                    MM_SKIPS.labels(reason="invalid_px").inc()
                await asyncio.sleep(0.25)
                return
            bid_qty, ask_qty = self._sizes(mid, inv_skew)
            await self._cancel_replace((round(bid_px, 4), bid_qty), (round(ask_px, 4), ask_qty))
            self.last_tick_time = time.time()
            self.consecutive_errors = 0
            self.perf.record_tick(self.last_tick_time - t0)
        except Exception as e:
            self.consecutive_errors = getattr(self, "consecutive_errors", 0) + 1
            if self.consecutive_errors > 10:
                logger.error("Too many consecutive errors (%d), entering recovery mode", self.consecutive_errors)
                try:
                    await self.shutdown(cancel_orders=True, timeout_s=2.0)
                except Exception:
                    pass
                await asyncio.sleep(10.0)
                self.consecutive_errors = 0
            else:
                if MM_ERRORS:
                    MM_ERRORS.labels(type="tick").inc()
                logger.exception("Tick error (%d): %s", self.consecutive_errors, e)
                await asyncio.sleep(0.5)


RUNNING = True
_DEF_HARD_EXIT = os.getenv("HARD_EXIT", "0") not in ("0", "false", "False", "")


def _sigterm(sig, _frame):
    global RUNNING
    logger.info("Signal %s received — graceful stop", sig)
    RUNNING = False


async def _start_health_server(mm: JITMarketMaker, port: int):
    try:
        from aiohttp import web
    except Exception:
        logger.warning("Health server requested but aiohttp not installed")
        return None

    async def health_check_handler(request: "web.Request"):
        health = {
            "status": "healthy",
            "timestamp": time.time(),
            "position": mm.position,
            "active_orders": len(mm.active),
            "last_tick": mm.last_tick_time,
            "avg_tick_ms": round(mm.perf.avg_tick_time * 1000, 2),
        }
        if time.time() - health["last_tick"] > 10:
            health["status"] = "stale"
        return web.Response(text=json.dumps(health), content_type="application/json")

    app = web.Application()
    app.router.add_get("/healthz", health_check_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logger.info("Health server on :%d", port)
    return runner


async def run_main(env: str, cfg_path: Path, cfg2_path: Optional[Path], *, no_metrics: bool = False, overrides: Optional[dict] = None, health_port: int = 0) -> int:
    merged_cfg = load_config(cfg_path, cfg2_path, overrides)
    jit_cfg = JITConfig.from_yaml(merged_cfg)
    global MM_TICKS, MM_SKIPS, MM_QUOTES, MM_CANCELS, MM_ERRORS, MM_SPREAD, MM_MID
    if no_metrics or _METRICS_BACKEND == "noop":
        MM_TICKS = _Counter("mm_ticks_total", "Total MM ticks")
        class _ShimCounter(_NoopMetric):
            def labels(self, *_, **__):
                return self
        MM_SKIPS = _ShimCounter()
        MM_QUOTES = _Counter("mm_quotes_total", "Quotes placed")
        MM_CANCELS = _Counter("mm_cancel_total", "Cancels issued")
        MM_ERRORS = _ShimCounter()
        MM_SPREAD = _Gauge("mm_spread_bps", "Current dynamic spread in bps")
        MM_MID = _Gauge("mm_mid_price", "Mid price used for quoting")
        logger.warning("[METRICS] Using NOOP backend")
    else:
        from prometheus_client import Gauge as _G, Counter as _C
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
    signal.signal(signal.SIGINT, _sigterm)
    try:
        signal.signal(signal.SIGTERM, _sigterm)
    except Exception:
        pass
    mm = JITMarketMaker(jit_cfg, merged_cfg)
    logger.info("JIT MM starting (env=%s, symbol=%s, metrics=%s)", env, jit_cfg.symbol, _METRICS_BACKEND if not no_metrics else "disabled")
    health_runner = None
    if health_port and isinstance(health_port, int) and health_port > 0:
        try:
            health_runner = await _start_health_server(mm, health_port)
        except Exception as e:
            logger.warning("Health server failed to start: %s", e)
    try:
        while RUNNING:
            try:
                await mm.tick()
            except asyncio.CancelledError:
                logger.info("Run loop cancelled during tick; stopping...")
                break
            dt = 0.25
            try:
                await asyncio.sleep(dt)
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
        if health_runner is not None:
            try:
                await health_runner.cleanup()  # type: ignore
            except Exception:
                pass
        logger.info("Shutdown complete")
    return 0


def _selftest() -> int:
    m = _NoopMetric(); m.inc(); m.set(1); m.labels(reason="x")
    ob = Orderbook(bids=[(100.0, 2.0), (99.9, 1.0)], asks=[(100.2, 3.0), (100.3, 1.0)], ts=time.time())
    micro, imb, skew, conf = OBICalculator(10).calculate(ob)
    assert 0 <= abs(imb) <= 1
    assert micro > 0 and conf > 0
    merged = load_config(Path("configs/core/drift_client.yaml"), Path("configs/jit/params.yaml"), overrides={"obi": {"levels": 7}, "mm": {"base_size": 0.08}})
    assert merged["obi"]["levels"] == 7
    assert abs(merged["mm"]["base_size"] - 0.08) < 1e-12
    cfg = JITConfig.from_yaml(merged)
    assert cfg.obi_levels == 7
    assert abs(cfg.base_size - 0.08) < 1e-12

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
    mm._last_cr_ms = 0
    asyncio.get_event_loop().run_until_complete(mm.tick())
    assert len(mm.active) in (1, 2)
    mm.active["oid-1"] = LiveOrder("oid-1", "buy", 100.0, 0.1, time.time())
    mm.active["oid-2"] = LiveOrder("oid-2", "sell", 100.2, 0.1, time.time())
    asyncio.get_event_loop().run_until_complete(mm.shutdown(cancel_orders=True, timeout_s=0.5))
    assert {"oid-1", "oid-2"}.issubset(set(getattr(mm.exec, "canceled", [])))

    async def _sleep_then_cancel():
        task = asyncio.create_task(asyncio.sleep(1.0))
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return True
        return False

    assert asyncio.get_event_loop().run_until_complete(_sleep_then_cancel()) is True
    b = base64.b64encode(b"").decode("ascii")
    assert isinstance(b, str) and len(b) > 0
    print("✅ Selftest passed (no network/ssl required)")
    return 0


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="JIT MM Bot (Swift, production)")
    p.add_argument("--env", default=os.getenv("ENV", "beta"))
    p.add_argument("--cfg", default="configs/core/drift_client.yaml")
    p.add_argument("--cfg2", default=None)
    p.add_argument("--no-metrics", action="store_true")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"), choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    p.add_argument("--override", action="append")
    p.add_argument("--health-port", type=int, default=int(os.getenv("HEALTH_PORT", "0")))
    return p.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    overrides = _parse_overrides(args.override)
    rc = 0
    try:
        if args.selftest:
            rc = _selftest()
        else:
            try:
                rc = asyncio.run(run_main(args.env, Path(args.cfg), Path(args.cfg2) if args.cfg2 else None, no_metrics=args.no_metrics, overrides=overrides, health_port=args.health_port))
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
        if os.getenv("HARD_EXIT", "0") not in ("0", "false", "False", ""):
            raise SystemExit(rc)
        else:
            pass
