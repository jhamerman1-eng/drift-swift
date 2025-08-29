#!/usr/bin/env python3
"""
Execute One Trade in Each Bot
Demonstrates Hedge, Trend, and JIT bot functionality by placing one trade each
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Setup basic logging (no emojis to avoid encoding issues)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_hedge_bot_trade():
    """Execute one trade with the Hedge Bot"""
    logger.info("=" * 60)
    logger.info("STARTING HEDGE BOT TRADE")
    logger.info("=" * 60)

    try:
        # Import hedge bot components
        sys.path.append('bots/hedge')
        from bots.hedge.main import hedge_iteration
        from libs.drift.client import build_client_from_config
        from libs.order_management import PositionTracker, OrderManager
        from orchestrator.risk_manager import RiskManager

        # Build client
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        # Initialize components
        position = PositionTracker()
        orders = OrderManager()
        risk_mgr = RiskManager()

        # Load hedge config
        import yaml
        with open('configs/hedge/routing.yaml', 'r') as f:
            hedge_cfg = yaml.safe_load(f) or {}

        logger.info("Hedge Bot initialized successfully")
        logger.info(f"Current position: ${position.net_exposure:.2f}")

        # Execute one hedge iteration (this will place a trade if conditions are met)
        await hedge_iteration(hedge_cfg, client, risk_mgr, position, orders)

        logger.info("Hedge Bot trade completed!")
        logger.info(f"Final position: ${position.net_exposure:.2f}")

    except Exception as e:
        logger.error(f"Hedge Bot failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

async def run_trend_bot_trade():
    """Execute one trade with the Trend Bot"""
    logger.info("=" * 60)
    logger.info("STARTING TREND BOT TRADE")
    logger.info("=" * 60)

    try:
        # Import trend bot components
        sys.path.append('bots/trend')
        from bots.trend.main import trend_iteration
        from libs.drift.client import build_client_from_config
        from libs.order_management import PositionTracker, OrderManager
        from orchestrator.risk_manager import RiskManager
        from collections import deque
        import numpy as np

        # Build client
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        # Initialize components
        position = PositionTracker()
        orders = OrderManager()
        risk_mgr = RiskManager()

        # Load trend config
        import yaml
        with open('configs/trend/filters.yaml', 'r') as f:
            trend_cfg = yaml.safe_load(f) or {}

        # Initialize trend tracking data
        prices = deque(maxlen=100)
        macd_values = deque(maxlen=100)
        state_vars = {
            'ema_fast': 0.0,
            'ema_slow': 0.0,
            'ema_signal': 0.0,
            'macd_prev': 0.0
        }

        logger.info("Trend Bot initialized successfully")
        logger.info(f"Current position: ${position.net_exposure:.2f}")

        # Execute one trend iteration (this will place a trade if signal is detected)
        await trend_iteration(trend_cfg, client, risk_mgr, position, orders, prices, macd_values, state_vars)

        logger.info("Trend Bot trade completed!")
        logger.info(f"Final position: ${position.net_exposure:.2f}")

    except Exception as e:
        logger.error(f"Trend Bot failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

async def run_jit_bot_trade():
    """Execute one trade with the JIT Bot"""
    logger.info("=" * 60)
    logger.info("STARTING JIT BOT TRADE")
    logger.info("=" * 60)

    try:
        # Import JIT bot components
        sys.path.append('bots/jit')
        from bots.jit.main import jit_mm_iteration
        from libs.drift.client import build_client_from_config
        from libs.order_management import PositionTracker, OrderManager
        from orchestrator.risk_manager import RiskManager

        # Build client
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        # Initialize components
        position = PositionTracker()
        orders = OrderManager()
        risk_mgr = RiskManager()

        # Load JIT config
        import yaml
        with open('configs/jit/params.yaml', 'r') as f:
            jit_cfg = yaml.safe_load(f) or {}

        logger.info("JIT Bot initialized successfully")
        logger.info(f"Current position: ${position.net_exposure:.2f}")

        # Execute one JIT iteration (this will place market making quotes)
        await jit_mm_iteration(jit_cfg, client, risk_mgr, position, orders)

        logger.info("JIT Bot trade completed!")
        logger.info(f"Final position: ${position.net_exposure:.2f}")

    except Exception as e:
        logger.error(f"JIT Bot failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

async def main():
    """Run one trade in each bot"""
    logger.info("🚀 STARTING INDIVIDUAL BOT TRADES")
    logger.info("Will execute one trade in each of the three bots:")
    logger.info("1. 🔄 Hedge Bot")
    logger.info("2. 📈 Trend Bot")
    logger.info("3. ⚡ JIT Bot")

    # Run Hedge Bot trade
    await run_hedge_bot_trade()

    # Small delay between bots
    await asyncio.sleep(2)

    # Run Trend Bot trade
    await run_trend_bot_trade()

    # Small delay between bots
    await asyncio.sleep(2)

    # Run JIT Bot trade
    await run_jit_bot_trade()

    logger.info("=" * 60)
    logger.info("🎉 ALL BOT TRADES COMPLETED!")
    logger.info("Each bot has executed one trade cycle")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())


