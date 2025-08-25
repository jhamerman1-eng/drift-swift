#!/usr/bin/env python3
"""Trend Bot.

This module implements an asynchronous trend‑following strategy using
MACD, momentum and optional ATR/ADX filters as described in the
v16.9 release.  It leverages the new primitives (async Drift
client, risk manager, position/order tracking) introduced in
v1.17.0‑RC.  The bot maintains a rolling price history to compute
indicators and issues buy or sell orders when the signal meets
configured criteria.  Orders are recorded in an ``OrderManager`` and
exposures are tracked via ``PositionTracker``.

This is still a simplified implementation and does not account for
partial fills or slippage across multiple venues.  Real trading
implementations should subscribe to fills, update positions on
confirmation and handle order rejections.
"""

from __future__ import annotations

import asyncio
import collections
import os
import signal
from typing import Any, Dict, Deque

import yaml
import numpy as np

from libs.drift.client import build_client_from_config, Order, DriftClient
from libs.order_management import PositionTracker, OrderManager, OrderRecord
from orchestrator.risk_manager import RiskManager, RiskState


def load_trend_config(path: str) -> Dict[str, Any]:
    """Load trend configuration from YAML file with environment expansion."""
    text = os.path.expandvars(open(path, "r").read())
    return yaml.safe_load(text) or {}


def ema(prev: float, value: float, k: float) -> float:
    """Compute one step of an exponential moving average."""
    return value * k + prev * (1.0 - k)


async def trend_iteration(cfg: Dict[str, Any], client: DriftClient, risk_mgr: RiskManager,
                          position: PositionTracker, orders: OrderManager,
                          prices: Deque[float], macd_values: Deque[float],
                          state_vars: Dict[str, float]) -> None:
    """Perform a single iteration of trend signal evaluation and order placement."""
    trend_cfg = cfg.get("trend", {})
    # Fetch price
    try:
        ob = await client.get_orderbook()
        if not ob.bids or not ob.asks:
            return
        price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
    except Exception:
        return
    prices.append(price)
    # Initialise EMAs if first run
    if state_vars.get("ema_fast") is None:
        state_vars["ema_fast"] = price
        state_vars["ema_slow"] = price
    # MACD parameters
    fast = trend_cfg.get("macd", {}).get("fast", 12)
    slow = trend_cfg.get("macd", {}).get("slow", 26)
    signal_period = trend_cfg.get("macd", {}).get("signal", 9)
    k_fast = 2.0 / (fast + 1)
    k_slow = 2.0 / (slow + 1)
    k_signal = 2.0 / (signal_period + 1)
    # Update EMAs
    state_vars["ema_fast"] = ema(state_vars["ema_fast"], price, k_fast)
    state_vars["ema_slow"] = ema(state_vars["ema_slow"], price, k_slow)
    macd_val = state_vars["ema_fast"] - state_vars["ema_slow"]
    macd_values.append(macd_val)
    # Compute signal line using a simple EMA on the MACD values
    if state_vars.get("ema_signal") is None:
        state_vars["ema_signal"] = macd_val
    state_vars["ema_signal"] = ema(state_vars["ema_signal"], macd_val, k_signal)
    hist = macd_val - state_vars["ema_signal"]
    # Momentum
    window = int(trend_cfg.get("momentum_window", 14))
    if len(prices) > window:
        momentum = price - prices[-(window+1)]
    else:
        momentum = 0.0
    # Optional ATR/ADX filters (not fully implemented)
    filters_cfg = trend_cfg.get("atr_adx_filters", {})
    if filters_cfg.get("enabled", False):
        # Placeholder: skip trade decisions if filters not satisfied
        pass
    # Determine trade direction and magnitude
    # We simply check sign of hist and momentum; in a real implementation
    # you could look for crossovers, thresholding etc.
    signal_strength = 0.0
    if trend_cfg.get("use_macd", True):
        signal_strength += hist
    signal_strength += momentum / max(price, 1e-9)
    # Scale by position_scaler and max_position_usd
    scaler = float(trend_cfg.get("position_scaler", 0.1))
    max_pos = float(trend_cfg.get("max_position_usd", 5000))
    notional = scaler * signal_strength * max_pos
    # Determine side based on notional
    if abs(notional) < 1.0:  # ignore tiny signals
        return
    side = "buy" if notional > 0 else "sell"
    size_usd = abs(notional)
    # Consult risk manager
    state: RiskState = risk_mgr.evaluate(price)
    perms = risk_mgr.decisions(state)
    if not perms.get("allow_trading", False) or not perms.get("allow_trend", True):
        await client.cancel_all()
        orders.cancel_all()
        return
    # Compute limit price with a small slippage premium
    slippage_bps = 5  # default slippage for trend entries
    slip = slippage_bps / 10_000.0
    # Best quotes
    best_bid = ob.bids[0][0]
    best_ask = ob.asks[0][0]
    price_with_slip = best_ask * (1.0 + slip) if side == "buy" else best_bid * (1.0 - slip)
    order = Order(side=side, price=price_with_slip, size_usd=size_usd)
    oid = await client.place_order(order)
    orders.add_order(OrderRecord(order_id=oid, side=side, price=price_with_slip, size_usd=size_usd))
    position.update(side, size_usd)


async def run_trend_bot(cfg: Dict[str, Any], client: DriftClient, risk_mgr: RiskManager,
                        position: PositionTracker, orders: OrderManager,
                        refresh_interval: float = 1.0) -> None:
    """Continuously evaluate trend signals and submit orders."""
    prices: Deque[float] = collections.deque(maxlen=1000)
    macd_values: Deque[float] = collections.deque(maxlen=1000)
    state_vars: Dict[str, float] = {}
    while True:
        await trend_iteration(cfg, client, risk_mgr, position, orders, prices, macd_values, state_vars)
        await asyncio.sleep(refresh_interval)


async def main() -> None:
    """Configure and launch the trend bot."""
    trend_cfg_path = os.getenv("TREND_CFG", "configs/trend/filters.yaml")
    cfg = load_trend_config(trend_cfg_path)
    drift_cfg_path = os.getenv("DRIFT_CFG", "configs/core/drift_client.yaml")
    client: DriftClient = await build_client_from_config(drift_cfg_path)
    risk_mgr = RiskManager()
    position = PositionTracker()
    orders = OrderManager()
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def request_stop() -> None:
        stop_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, request_stop)
        loop.add_signal_handler(signal.SIGTERM, request_stop)
    except NotImplementedError:
        pass
    # Launch trend loop
    bot_task = asyncio.create_task(run_trend_bot(cfg, client, risk_mgr, position, orders))
    await stop_event.wait()
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass
    # Clean up
    if hasattr(client, "close") and asyncio.iscoroutinefunction(client.close):
        try:
            await client.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())