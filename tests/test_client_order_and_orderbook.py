
import time
import unittest
from types import SimpleNamespace

# Minimal Orderbook type used by the client
class Orderbook:
    def __init__(self, bids=None, asks=None):
        self.bids = bids or []
        self.asks = asks or []

# Fake drivers to simulate venue/sidecar behavior
class AlwaysOKDriver:
    name = "AlwaysOK"
    def __init__(self, tx_prefix="ok"):
        self._last_order = None
        self.ob = Orderbook(bids=[(100.0, 10.0)], asks=[(100.2, 10.0)])
        self.tx_prefix = tx_prefix
    def place_order(self, order):
        self._last_order = order
        return f"{self.tx_prefix}_{getattr(order, 'side', 'S')}_{abs(getattr(order, 'qty', 0)):.6f}"
    def get_orderbook(self):
        return self.ob

class Always429Driver:
    name = "Always429"
    def place_order(self, order):
        raise Exception("HTTP 429: Rate limit exceeded")
    def get_orderbook(self):
        raise Exception("HTTP 429: Too many requests")

class TimeoutDriver:
    name = "Timeout"
    def place_order(self, order):
        raise Exception("WebSocket connection timeout")
    def get_orderbook(self):
        raise Exception("WebSocket connection timeout")

class RejectDriver:
    name = "Reject"
    def place_order(self, order):
        raise Exception("400 Bad Request: rejected")
    def get_orderbook(self):
        raise Exception("400 Bad Request: invalid")

class FlakyThenOKDriver:
    name = "FlakyThenOK"
    def __init__(self, fails=2):
        self.fails = fails
        self.ok = AlwaysOKDriver(tx_prefix="flaky_ok")
    def place_order(self, order):
        if self.fails > 0:
            self.fails -= 1
            raise Exception("HTTP 429: Rate limit exceeded")
        return self.ok.place_order(order)
    def get_orderbook(self):
        if self.fails > 0:
            self.fails -= 1
            raise Exception("WebSocket connection timeout")
        return self.ok.get_orderbook()

# ClientUnderTest replicates the production-grade logic for the two methods only.
# We keep it minimal and self-contained for unit testing.
class ClientUnderTest:
    def __init__(self, primary, fallback=None, fallback_active=False):
        import logging
        self.logger = logging.getLogger("ClientUnderTest")
        self.driver = primary
        self.fallback_driver = fallback
        self.fallback_active = fallback_active
        # Tunables
        self.max_retries = 5
        self.base_backoff_seconds = 0.01   # use tiny delays for fast tests
        self.max_backoff_seconds = 0.05
        self.orderbook_ttl_seconds = 0.25
        self.orderbook_max_stale_seconds = 1.0
        self.qty_step = 0.0
        # Cache
        self._ob_cache = None
        self._ob_cache_ts = 0.0

    # ---- Code under test: place_order ----
    def place_order(self, order):
        import math, random, time as tmod

        def _classify(exc: Exception) -> str:
            m = str(exc)
            if "429" in m or "Rate limit" in m:
                return "rate_limit"
            if "timeout" in m.lower() or "timed out" in m.lower():
                return "timeout"
            if "connection" in m.lower() or "websocket" in m.lower():
                return "network"
            if "rejected" in m.lower() or "400" in m or "403" in m:
                return "rejected"
            return "unknown"

        def _sleep(attempt: int) -> None:
            delay = min(self.max_backoff_seconds,
                        (self.base_backoff_seconds * (2 ** (attempt - 1))) * (1 + random.random()))
            # Patchable in tests if needed
            time.sleep(delay)

        qty = getattr(order, "qty", None)
        usd = getattr(order, "usd_size", None)

        if (qty is None or qty == 0) and (usd is not None and usd != 0):
            ob = self.get_orderbook()
            best_bid = ob.bids[0][0] if ob.bids else None
            best_ask = ob.asks[0][0] if ob.asks else None
            mid = None
            if best_bid and best_ask:
                mid = 0.5 * (best_bid + best_ask)
            elif best_bid:
                mid = best_bid
            elif best_ask:
                mid = best_ask

            if mid is None or mid <= 0:
                raise RuntimeError("No valid price available for USD→qty conversion")

            qty = usd / mid
            side = getattr(order, "side", "buy").lower()
            if side == "sell" and qty > 0:
                qty = -qty

            step = float(getattr(self, "qty_step", 0.0)) or float(getattr(order, "qty_step", 0.0)) or 0.0
            if step > 0:
                qty = math.copysign(max(0.0, abs(round(qty / step) * step)), qty)

            setattr(order, "qty", qty)

        if qty is None or abs(qty) <= 0.0:
            raise RuntimeError("Order qty is zero/None after sizing")
        if not hasattr(order, "side"):
            raise RuntimeError("Order missing side (buy/sell)")

        drivers = [self.driver]
        if self.fallback_active and self.fallback_driver is not None:
            drivers.append(self.fallback_driver)

        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            for idx, drv in enumerate(drivers):
                try:
                    tx_sig = drv.place_order(order)
                    if not tx_sig or not isinstance(tx_sig, str):
                        raise RuntimeError("Driver returned empty/invalid tx signature")
                    return tx_sig
                except Exception as e:
                    last_exc = e
                    kind = _classify(e)
                    if kind == "rejected":
                        raise
                    if idx == 0 and self.fallback_active and self.fallback_driver is not None:
                        continue
                    if attempt < self.max_retries and kind in {"rate_limit", "timeout", "network", "unknown"}:
                        _sleep(attempt)
                    else:
                        if attempt >= self.max_retries:
                            raise
        raise RuntimeError(f"Failed to place order after {self.max_retries} attempts: {last_exc}")

    # ---- Code under test: get_orderbook ----
    def get_orderbook(self):
        import random

        now = time.time()
        if self._ob_cache and (now - self._ob_cache_ts) <= self.orderbook_ttl_seconds:
            return self._ob_cache

        def _sleep(attempt: int) -> None:
            delay = min(self.max_backoff_seconds,
                        (self.base_backoff_seconds * (2 ** (attempt - 1))) * (1 + random.random()))
            time.sleep(delay)

        def _classify(exc: Exception) -> str:
            m = str(exc)
            if "429" in m or "Too many requests" in m:
                return "rate_limit"
            if "timeout" in m.lower():
                return "timeout"
            if "websocket" in m.lower() or "connection" in m.lower():
                return "network"
            return "unknown"

        drivers = [self.driver]
        if self.fallback_active and self.fallback_driver is not None:
            drivers.append(self.fallback_driver)

        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            for idx, drv in enumerate(drivers):
                try:
                    ob = drv.get_orderbook()
                    def _ok_side(side):
                        return bool(side) and all(p > 0 and sz >= 0 for p, sz in side)
                    if ob is None or (not _ok_side(ob.bids) and not _ok_side(ob.asks)):
                        raise RuntimeError("Driver returned invalid orderbook")
                    self._ob_cache = ob
                    self._ob_cache_ts = time.time()
                    return ob
                except Exception as e:
                    last_exc = e
                    kind = _classify(e)
                    if idx == 0 and self.fallback_active and self.fallback_driver is not None:
                        continue
                    if attempt < self.max_retries:
                        _sleep(attempt)
                    else:
                        pass

        if self._ob_cache and (time.time() - self._ob_cache_ts) <= self.orderbook_max_stale_seconds:
            return self._ob_cache
        raise RuntimeError(f"Failed to fetch orderbook after {self.max_retries} attempts: {last_exc}")


class TestPlaceOrderAndOrderbook(unittest.TestCase):
    def setUp(self):
        # Speed up tests by neutralizing time.sleep
        self._orig_sleep = time.sleep
        time.sleep = lambda s: None

    def tearDown(self):
        time.sleep = self._orig_sleep

    # --- place_order tests ---

    def test_place_order_primary_ok(self):
        client = ClientUnderTest(primary=AlwaysOKDriver())
        order = SimpleNamespace(side="buy", qty=1.0, usd_size=None)
        sig = client.place_order(order)
        self.assertTrue(sig.startswith("ok_buy_"))

    def test_place_order_usd_to_qty_conversion(self):
        # mid ~ 100.1 → qty ≈ 10 if usd=~1001
        drv = AlwaysOKDriver()
        drv.ob = Orderbook(bids=[(100.0, 10)], asks=[(100.2, 10)])
        client = ClientUnderTest(primary=drv)
        order = SimpleNamespace(side="sell", qty=None, usd_size=1001.0, qty_step=0.0)
        sig = client.place_order(order)
        self.assertLess(getattr(order, "qty"), 0.0)  # sell makes qty negative when derived
        # simple sanity: qty magnitude ~ usd / mid
        mid = 0.5 * (100.0 + 100.2)
        self.assertAlmostEqual(abs(order.qty), 1001.0 / mid, places=6)
        self.assertTrue(sig.startswith("ok_sell_"))

    def test_place_order_fallback_on_429(self):
        client = ClientUnderTest(primary=Always429Driver(), fallback=AlwaysOKDriver(tx_prefix="fb"), fallback_active=True)
        order = SimpleNamespace(side="buy", qty=2.0, usd_size=None)
        sig = client.place_order(order)
        self.assertTrue(sig.startswith("fb_buy_"))

    def test_place_order_retry_then_success(self):
        client = ClientUnderTest(primary=FlakyThenOKDriver(fails=2))
        order = SimpleNamespace(side="buy", qty=1.5, usd_size=None)
        sig = client.place_order(order)
        self.assertTrue(sig.startswith("flaky_ok_buy_"))

    def test_place_order_rejected_does_not_retry(self):
        client = ClientUnderTest(primary=RejectDriver(), fallback=AlwaysOKDriver(), fallback_active=True)
        order = SimpleNamespace(side="buy", qty=1.0, usd_size=None)
        with self.assertRaises(Exception):
            client.place_order(order)

    def test_place_order_raises_if_zero_qty_after_sizing(self):
        client = ClientUnderTest(primary=AlwaysOKDriver())
        order = SimpleNamespace(side="buy", qty=0.0, usd_size=None)
        with self.assertRaises(RuntimeError):
            client.place_order(order)

    # --- get_orderbook tests ---

    def test_get_orderbook_primary_ok(self):
        client = ClientUnderTest(primary=AlwaysOKDriver())
        ob = client.get_orderbook()
        self.assertTrue(ob.bids and ob.asks)

    def test_get_orderbook_uses_cache_within_ttl(self):
        drv = AlwaysOKDriver()
        client = ClientUnderTest(primary=drv)
        ob1 = client.get_orderbook()
        # mutate driver ob; within TTL, cached should still be returned
        drv.ob = Orderbook(bids=[(1.0, 1.0)], asks=[(2.0, 1.0)])
        ob2 = client.get_orderbook()
        self.assertIs(ob1, ob2)  # same object due to cache

    def test_get_orderbook_fallback_on_failure(self):
        client = ClientUnderTest(primary=TimeoutDriver(), fallback=AlwaysOKDriver(), fallback_active=True)
        ob = client.get_orderbook()
        self.assertTrue(ob.bids and ob.asks)

    def test_get_orderbook_returns_stale_on_persistent_failures(self):
        # First get a good cache
        ok = AlwaysOKDriver()
        client = ClientUnderTest(primary=ok)
        ob1 = client.get_orderbook()
        # Replace driver with permanent failures
        client.driver = TimeoutDriver()
        # Age cache slightly but within max_stale
        client._ob_cache_ts = time.time() - (client.orderbook_ttl_seconds + 0.1)
        ob2 = client.get_orderbook()  # should return stale
        self.assertIs(ob1, ob2)

    def test_get_orderbook_raises_when_no_cache_and_failures(self):
        client = ClientUnderTest(primary=Always429Driver())
        with self.assertRaises(RuntimeError):
            client.get_orderbook()

if __name__ == "__main__":
    unittest.main()
