#!/usr/bin/env python3
"""Hedge Bot.

This module implements an asynchronous hedging strategy that neutralises
inventory exposure using the new primitives introduced in v1.17.0‑RC.
It loads a routing configuration from ``configs/hedge/routing.yaml``,
computes the current net exposure from ``PositionTracker``, then
decides whether to hedge via a passive or an IOC route.  Orders are
sent through a ``DriftClient`` instance (mock or real) and recorded in
an ``OrderManager``.  The risk manager is consulted before each
operation to respect drawdown thresholds.

The hedge loop runs continuously until a SIGINT or SIGTERM is
received.  It will sleep for a configurable interval between
iterations.
"""

from __future__ import annotations

import asyncio
import os
import signal
from typing import Any, Dict

import yaml

from libs.drift.client import build_client_from_config, Order, DriftClient
from libs.order_management import PositionTracker, OrderManager, OrderRecord
from orchestrator.risk_manager import RiskManager, RiskState
from bots.hedge.decide import decide_hedge, HedgeInputs, HedgeDecision
from bots.hedge.execution import execute_hedge


def load_hedge_config(path: str) -> Dict[str, Any]:
    """Load the hedge routing configuration from a YAML file.

    Environment variables in the file will be expanded.  See
    ``configs/hedge/routing.yaml`` for an example.
    """
    text = os.path.expandvars(open(path, "r").read())
    return yaml.safe_load(text) or {}


async def hedge_iteration(cfg: Dict[str, Any], client: DriftClient, risk_mgr: RiskManager,
                          position: PositionTracker, orders: OrderManager) -> None:
    """Perform a single hedging iteration with safe decision making.

    This function reads the current net exposure, gathers market data,
    and uses the safe decision engine to determine hedging actions.
    Prevents division by zero errors when ATR, equity, or price are zero/None.
    """
    # Check risk rails first; mid price is used as a proxy for account equity
    try:
        ob = await client.get_orderbook()
        if not ob.bids or not ob.asks:
            return
        best_bid = ob.bids[0][0]
        best_ask = ob.asks[0][0]
        mid_price = (best_bid + best_ask) / 2.0
    except Exception:
        # If the orderbook fetch fails, skip this iteration
        return

    state: RiskState = risk_mgr.evaluate(mid_price)
    perms = risk_mgr.decisions(state)
    if not perms.get("allow_trading", False):
        # Trading disabled: cancel all open orders and bail out
        try:
            await client.cancel_all()
        except:
            pass
        orders.cancel_all()
        return

    # Gather inputs for hedge decision
    current_delta_usd = position.net_exposure
    current_atr = None  # TODO: Implement ATR calculation
    account_equity_usd = None  # TODO: Get from account data

    # Create inputs for decision engine
    inp = HedgeInputs(
        net_exposure_usd=current_delta_usd,     # can be 0 in SIM
        mid_price=mid_price,                    # validate > 0
        atr=current_atr,                        # can be 0 at startup
        equity_usd=account_equity_usd           # 0/None in SIM
    )

    # Get hedge decision
    decision = decide_hedge(inp)

    if decision.action == "SKIP":
        # Log skip reason for monitoring
        print(f"[HEDGE] Skip: {decision.reason}")
        return

    # Execute hedge if decision is to trade
    if decision.action == "HEDGE":
        hedge_cfg = cfg.get("hedge", {})
        qty_usd = abs(decision.qty)  # Convert to positive notional

        # Determine side based on quantity sign
        side = "sell" if decision.qty < 0 else "buy"

        # Apply slippage based on route
        route_key = "ioc" if "urgency" in decision.reason and float(decision.reason.split("=")[1]) > 1.0 else "passive"
        slippage_bps = float(hedge_cfg.get(route_key, {}).get("max_slippage_bps", 5))
        slip = slippage_bps / 10_000.0

        # Calculate limit price with slippage
        price = best_bid * (1.0 - slip) if side == "sell" else best_ask * (1.0 + slip)

        # Execute the hedge decision
        venues = hedge_cfg.get(route_key, {}).get("venues", ["DEX_DRIFT"])
        execution_result = execute_hedge(decision, venues)
        print(f"[HEDGE] {execution_result}")

        # Place the hedge order
        try:
            order = Order(side=side, price=price, size_usd=qty_usd)
            order_id = client.place_order(order)
            orders.add_order(OrderRecord(order_id=order_id, side=side, price=price, size_usd=qty_usd))

            # Immediately adjust local position; in a real implementation this should
            # occur after a fill confirmation from the exchange
            position.update(side, qty_usd)

            print(f"[HEDGE] Executed {side.upper()} ${qty_usd:.2f} @ ${price:.4f} ({decision.reason})")
        except Exception as e:
            print(f"[HEDGE] Failed to place hedge order: {e}")
    else:
        # No-op; do not attempt any math downstream
        pass


async def run_hedge_bot(cfg: Dict[str, Any], client: DriftClient, risk_mgr: RiskManager,
                        position: PositionTracker, orders: OrderManager,
                        refresh_interval: float = 1.0) -> None:
    """Continuously hedge inventory exposure at a fixed cadence."""
    while True:
        await hedge_iteration(cfg, client, risk_mgr, position, orders)
        await asyncio.sleep(refresh_interval)


async def main() -> None:
    """Configure and launch the hedge bot."""
    # Load configuration files
    cfg_path = os.getenv("HEDGE_CFG", "configs/hedge/routing.yaml")
    cfg = load_hedge_config(cfg_path)
    # Build market client from drift config
    drift_cfg = os.getenv("DRIFT_CFG", "configs/core/drift_client.yaml")
    client: DriftClient = await build_client_from_config(drift_cfg)
    # Setup risk and bookkeeping
    risk_mgr = RiskManager()
    position = PositionTracker()
    orders = OrderManager()

    # Setup signal handling
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def request_stop() -> None:
        stop_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, request_stop)
        loop.add_signal_handler(signal.SIGTERM, request_stop)
    except NotImplementedError:
        pass

    # Launch hedge loop
    bot_task = asyncio.create_task(run_hedge_bot(cfg, client, risk_mgr, position, orders))
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