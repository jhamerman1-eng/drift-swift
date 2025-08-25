#!/usr/bin/env python3
"""JIT Maker Bot.

This module implements an asynchronous just‑in‑time (JIT) market making
strategy.  It ties together a market data client, a quoting strategy,
a risk manager, and simple order/position tracking.  The goal of
this implementation is to demonstrate how a production bot might
coordinate these components while remaining entirely non‑blocking.

Key features:

* **Async first**: uses ``asyncio`` to avoid blocking the event loop.
* **Configurable**: spread, quote size and refresh interval are
  controlled via environment variables.
* **Client agnostic**: uses the new ``build_client_from_config``
  helper to obtain a market data + execution client (mock or real).
* **Risk aware**: integrates with ``RiskManager`` to honour soft
  drawdown, trend pause and circuit breaker thresholds.
* **Order management**: utilises a ``PositionTracker`` and
  ``OrderManager`` to record fills and open orders.
* **Graceful shutdown**: handles SIGINT/SIGTERM and ensures that
  network resources are closed on exit.

The bot computes a mid price from the top of the orderbook on each
iteration, then places symmetric bid and ask orders around that mid.
If the risk manager signals that trading should be disabled (e.g. due
to a circuit breaker), the bot will cancel all open orders and skip
placing new ones.  Position and order tracking is updated whenever
an order is placed, but in this stub implementation fills are not
reported by the exchange so exposures do not change after placement.
To integrate with a real exchange, update the ``AsyncDriftClient``
to return order IDs and subscribe to fill events; then update
``PositionTracker`` accordingly.
"""

import asyncio
import os
import random
import signal
from dataclasses import dataclass
from typing import Optional

from orchestrator.risk_manager import RiskManager, RiskState
from libs.drift.client import build_client_from_config, Order, DriftClient
from libs.order_management import PositionTracker, OrderManager, OrderRecord


@dataclass
class QuoteParams:
    """Configuration for the quoting strategy."""
    spread_bps: float
    quote_size_usd: float
    refresh_interval: float  # seconds


async def run_jit_bot(params: QuoteParams, risk_mgr: RiskManager, client: DriftClient, position: PositionTracker, orders: OrderManager) -> None:
    """Run the JIT market making loop until cancelled.

    This coroutine repeatedly fetches an orderbook snapshot, computes a
    mid price, and places symmetric bid/ask orders around that mid.  It
    consults the risk manager before each iteration to decide whether
    trading is permitted and whether quotes should be widened.  Order
    placements are recorded in the ``OrderManager``, but fills are not
    simulated.

    Parameters
    ----------
    params : QuoteParams
        Tunable quoting parameters.
    risk_mgr : RiskManager
        Object responsible for enforcing drawdown limits.
    client : DriftClient
        Market data + execution client.
    position : PositionTracker
        Tracks net exposure.  Updated after each order placement.
    orders : OrderManager
        Registry of open orders.
    """
    while True:
        # Fetch top‑of‑book to compute mid.  On error, skip this iteration.
        try:
            ob = await client.get_orderbook()
            if not ob.bids or not ob.asks:
                raise RuntimeError("empty orderbook")
            best_bid, _ = ob.bids[0]
            best_ask, _ = ob.asks[0]
            mid = (best_bid + best_ask) / 2.0
        except Exception as exc:
            print(f"[JIT] failed to fetch orderbook: {exc}")
            await asyncio.sleep(params.refresh_interval)
            continue

        # Compute bid/ask around mid price.
        half_spread = params.spread_bps / 2.0 / 10_000.0
        bid = mid * (1.0 - half_spread)
        ask = mid * (1.0 + half_spread)

        # Evaluate risk state using net equity as mid for simplicity.  A real
        # implementation would use account equity from the exchange.
        state: RiskState = risk_mgr.evaluate(mid)
        perms = risk_mgr.decisions(state)

        if perms["allow_trading"]:
            # Optionally widen spreads to reduce quote aggressiveness.
            if perms.get("tighten_quotes"):
                bid *= 0.99
                ask *= 1.01

            # Place buy order
            buy_order = Order(side="buy", price=bid, size_usd=params.quote_size_usd)
            buy_oid = await client.place_order(buy_order)
            orders.add_order(OrderRecord(order_id=buy_oid, side="buy", price=bid, size_usd=params.quote_size_usd))
            position.update("buy", params.quote_size_usd)

            # Place sell order
            sell_order = Order(side="sell", price=ask, size_usd=params.quote_size_usd)
            sell_oid = await client.place_order(sell_order)
            orders.add_order(OrderRecord(order_id=sell_oid, side="sell", price=ask, size_usd=params.quote_size_usd))
            position.update("sell", params.quote_size_usd)
        else:
            print("[JIT] trading disabled due to circuit breaker")
            await client.cancel_all()
            orders.cancel_all()

        await asyncio.sleep(params.refresh_interval)


def parse_params() -> QuoteParams:
    """Parse quoting parameters from environment variables."""
    spread = float(os.getenv("SPREAD_BPS", "6.0"))
    size = float(os.getenv("QUOTE_SIZE_USD", "200.0"))
    refresh_ms = float(os.getenv("JIT_REFRESH_MS", "500.0"))
    return QuoteParams(
        spread_bps=spread,
        quote_size_usd=size,
        refresh_interval=refresh_ms / 1000.0,
    )


async def main() -> None:
    """Entry point: configure and run the JIT bot."""
    params = parse_params()
    risk_mgr = RiskManager()
    position = PositionTracker()
    orders = OrderManager()

    # Build market client from YAML configuration.  Users can override
    # DRIFT_CFG via the environment.  If the YAML sets ``use_mock: true``
    # the returned client will be a ``MockDriftClient``; otherwise an
    # ``AsyncDriftClient`` is constructed.
    cfg_path = os.getenv("DRIFT_CFG", "configs/core/drift_client.yaml")
    client: DriftClient = await build_client_from_config(cfg_path)

    # Set up signal handlers for graceful shutdown.
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _request_stop() -> None:
        stop_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, _request_stop)
        loop.add_signal_handler(signal.SIGTERM, _request_stop)
    except NotImplementedError:
        # Signal handlers are not supported on Windows when using ProactorEventLoop
        pass

    # Run the bot until a termination signal is received.
    bot_task = asyncio.create_task(run_jit_bot(params, risk_mgr, client, position, orders))
    await stop_event.wait()
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass
    print("[JIT] shutdown complete")
    # Close network resources
    try:
        close = getattr(client, "close", None)
        if asyncio.iscoroutinefunction(close):
            await close()
    except Exception:
        pass

if __name__ == "__main__":
    asyncio.run(main())
