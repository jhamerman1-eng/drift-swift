#!/usr/bin/env python3
"""Debug script for investigating order limits and Drift protocol issues."""

import asyncio
import inspect
import logging
import os
from typing import Any

from libs.drift.client import build_client_from_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _maybe_await(value: Any) -> Any:
    """Await value if it is an awaitable."""
    if inspect.isawaitable(value):
        return await value
    return value


async def debug_order_state() -> bool:
    """Debug the current order state and Drift protocol limits."""
    try:
        logger.info("Starting order limit debugging...")
        os.environ["DRIFT_ENV"] = "devnet"

        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()
        await client._ensure_ready()  # type: ignore[attr-defined]

        driver = getattr(client, "_driver", None)
        if driver is None:
            logger.error("Drift client driver is not available")
            return False

        logger.info("Checking user account state...")
        try:
            user = driver.get_user(0)
            user_account = user.get_user_account() if user else None
            if not user_account:
                logger.error("No user account found after initialization")
                return False
            logger.info("User account is available")
        except Exception as e:
            logger.error(f"Error retrieving user account: {e}")
            return False

        user_stats_fn = getattr(driver, "get_user_stats", None)
        if callable(user_stats_fn):
            try:
                user_stats = await _maybe_await(user_stats_fn())
                logger.info("User stats fetched successfully")
                logger.debug("User stats: %s", user_stats)
            except Exception as exc:
                logger.warning("Could not fetch user stats: %s", exc)

        open_orders_fn = getattr(driver, "get_open_orders", None)
        if callable(open_orders_fn):
            try:
                open_orders = await _maybe_await(open_orders_fn())
                order_count = len(open_orders) if open_orders else 0
                logger.info("Open orders count: %s", order_count)
                for index, order in enumerate(open_orders[:5] if open_orders else []):
                    logger.debug("Order %s: %s", index + 1, order)
            except Exception as exc:
                logger.warning("Could not fetch open orders: %s", exc)

        logger.info("Testing minimal order placement (dry run)...")
        try:
            from libs.order_management import Order, OrderSide

            test_order = Order(side=OrderSide.BUY, price=100000, size_usd=0.01)
            result = await client.place_order(test_order)
            logger.info("Test order placement result: %s", result)
        except Exception as exc:
            logger.error("Test order placement failed: %s", exc)

        return True

    except Exception as exc:
        logger.error("Debug script failed: %s", exc)
        logger.exception("Traceback for debug failure")
        return False


if __name__ == "__main__":
    success = asyncio.run(debug_order_state())
    if success:
        logger.info("Debug analysis complete")
    else:
        logger.error("Debug analysis failed")
