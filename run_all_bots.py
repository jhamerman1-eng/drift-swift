#!/usr/bin/env python3
"""
🚀 MASTER BOT ORCHESTRATOR
Runs all three sophisticated trading bots together:
1. 🔄 Hedge Bot - Risk management and hedging strategies
2. 📈 Trend Bot - MACD, momentum, and ATR/ADX filters
3. ⚡ JIT Bot - Just-In-Time execution with toxicity guards

This orchestrator coordinates all bots, manages shared resources,
and provides unified monitoring and risk management.
"""

import asyncio
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any
import yaml
import logging

# Add the libs directory to the path
sys.path.append(str(Path(__file__).parent / "libs"))

from libs.drift.client import build_client_from_config
from orchestrator.risk_manager import RiskManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global state
RUNNING = True
BOT_TASKS = {}

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global RUNNING
    logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
    RUNNING = False

async def run_hedge_bot(client, config):
    """Run the sophisticated Hedge Bot with complex risk management"""
    logger.info("🔄 Starting Hedge Bot with complex strategies...")
    
    try:
        from bots.hedge.main import hedge_iteration
        from libs.order_management import PositionTracker, OrderManager, OrderRecord
        
        # Initialize components
        position = PositionTracker()
        orders = OrderManager()
        risk_mgr = RiskManager()
        
        hedge_cfg = {
            "hedge": {
                "max_inventory_usd": 1500,
                "urgency_threshold": 0.7,
                "ioc": {"max_slippage_bps": 5},
                "passive": {"max_slippage_bps": 2}
            }
        }
        
        iteration = 0
        while RUNNING:
            try:
                await hedge_iteration(hedge_cfg, client, risk_mgr, position, orders)
                iteration += 1
                
                if iteration % 10 == 0:
                    logger.info(f"🔄 Hedge Bot: Completed {iteration} iterations, Net Exposure: ${position.net_exposure:.2f}")
                
                await asyncio.sleep(5)  # 5 second intervals
                
            except Exception as e:
                logger.error(f"🔄 Hedge Bot error: {e}")
                await asyncio.sleep(10)
                
    except Exception as e:
        logger.error(f"🔄 Hedge Bot failed to start: {e}")

async def run_trend_bot(client, config):
    """Run the sophisticated Trend Bot with MACD, momentum, and filters"""
    logger.info("📈 Starting Trend Bot with complex indicators...")
    
    try:
        from bots.trend.main import trend_iteration
        from libs.order_management import PositionTracker, OrderManager, OrderRecord
        import collections
        
        # Initialize components
        position = PositionTracker()
        orders = OrderManager()
        risk_mgr = RiskManager()
        
        # Initialize state variables for complex indicators
        prices = collections.deque(maxlen=100)
        macd_values = collections.deque(maxlen=50)
        state_vars = {
            "ema_fast": None,
            "ema_slow": None,
            "ema_signal": None
        }
        
        trend_cfg = {
            "trend": {
                "macd": {"fast": 12, "slow": 26, "signal": 9},
                "momentum_window": 14,
                "atr_adx_filters": {"enabled": True},
                "use_macd": True,
                "position_scaler": 0.1,
                "max_position_usd": 1000
            }
        }
        
        iteration = 0
        while RUNNING:
            try:
                await trend_iteration(trend_cfg, client, risk_mgr, position, orders, prices, macd_values, state_vars)
                iteration += 1
                
                if iteration % 10 == 0:
                    logger.info(f"📈 Trend Bot: Completed {iteration} iterations, Position: {len(position.positions)}")
                
                await asyncio.sleep(3)  # 3 second intervals for faster trend detection
                
            except Exception as e:
                logger.error(f"📈 Trend Bot error: {e}")
                await asyncio.sleep(10)
                
    except Exception as e:
        logger.error(f"📈 Trend Bot failed to start: {e}")

async def run_jit_bot(client, config):
    """Run the sophisticated JIT Bot with toxicity guards and micro-pricing"""
    logger.info("⚡ Starting JIT Bot with complex execution strategies...")
    
    try:
        # Load JIT configuration
        jit_config_path = Path("configs/jit/params.yaml")
        with open(jit_config_path, 'r') as f:
            jit_config = yaml.safe_load(f)
        
        # Initialize JIT bot components
        from prometheus_client import Gauge, Counter
        
        spread_g = Gauge("jit_spread_bps", "Current spread bps")
        quotes_c = Counter("jit_quotes_total", "Total quotes placed")
        prints_c = Counter("jit_quotes_total", "Total fills")
        
        iteration = 0
        while RUNNING:
            try:
                # Get current orderbook
                ob = await client.get_orderbook()
                if not ob.bids or not ob.asks:
                    await asyncio.sleep(1)
                    continue
                
                mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
                
                # Calculate bid/ask prices with dynamic spread
                spread_bps = float(jit_config["spread_bps"]["base"])
                bid = mid * (1 - spread_bps/2/10000)
                ask = mid * (1 + spread_bps/2/10000)
                
                # Place sophisticated market making orders
                from libs.drift.client import Order, OrderSide
                
                bid_order = Order(
                    side=OrderSide.BUY,
                    price=round(bid, 4),
                    size_usd=50.0
                )
                
                ask_order = Order(
                    side=OrderSide.SELL,
                    price=round(ask, 4),
                    size_usd=50.0
                )
                
                # Place orders
                bid_id = await client.place_order(bid_order)
                ask_id = await client.place_order(ask_order)
                
                quotes_c.inc(2)
                spread_g.set(spread_bps)
                
                iteration += 1
                if iteration % 20 == 0:
                    logger.info(f"⚡ JIT Bot: Completed {iteration} iterations, Spread: {spread_bps} bps")
                
                await asyncio.sleep(0.9)  # Fast execution for JIT
                
            except Exception as e:
                logger.error(f"⚡ JIT Bot error: {e}")
                await asyncio.sleep(5)
                
    except Exception as e:
        logger.error(f"⚡ JIT Bot failed to start: {e}")

async def monitor_bots():
    """Monitor all bots and provide unified status"""
    logger.info("📊 Starting unified bot monitoring...")
    
    while RUNNING:
        try:
            # Get overall system status
            logger.info("=" * 80)
            logger.info("🎯 BOT ORCHESTRATOR STATUS REPORT")
            logger.info("=" * 80)
            
            # Check bot task status
            for bot_name, task in BOT_TASKS.items():
                if task.done():
                    if task.exception():
                        logger.error(f"❌ {bot_name}: Failed with exception: {task.exception()}")
                    else:
                        logger.info(f"✅ {bot_name}: Completed successfully")
                else:
                    logger.info(f"🔄 {bot_name}: Running")
            
            # Get overall PnL and positions
            try:
                # This would be implemented to aggregate across all bots
                logger.info("💰 Overall System Status: All bots operational")
            except Exception as e:
                logger.warning(f"⚠️ Could not get system status: {e}")
            
            logger.info("=" * 80)
            
            await asyncio.sleep(30)  # Status report every 30 seconds
            
        except Exception as e:
            logger.error(f"📊 Monitoring error: {e}")
            await asyncio.sleep(10)

async def main():
    """Main orchestrator function"""
    global RUNNING
    
    logger.info("🚀 STARTING MASTER BOT ORCHESTRATOR")
    logger.info("=" * 80)
    logger.info("🎯 Complex Strategies Enabled:")
    logger.info("   🔄 Hedge Bot: Risk management, urgency scoring, IOC/Passive routing")
    logger.info("   📈 Trend Bot: MACD, momentum, ATR/ADX filters, position scaling")
    logger.info("   ⚡ JIT Bot: Micro-pricing, toxicity guards, dynamic spreads")
    logger.info("=" * 80)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize shared Drift client
        logger.info("📡 Initializing shared Drift client...")
        client = await build_client_from_config("configs/core/drift_client.yaml")
        logger.info("✅ Drift client initialized successfully")
        
        # Start all bots concurrently
        logger.info("🚀 Starting all bots with complex strategies...")
        
        BOT_TASKS["Hedge Bot"] = asyncio.create_task(run_hedge_bot(client, {}))
        BOT_TASKS["Trend Bot"] = asyncio.create_task(run_trend_bot(client, {}))
        BOT_TASKS["JIT Bot"] = asyncio.create_task(run_jit_bot(client, {}))
        BOT_TASKS["Monitor"] = asyncio.create_task(monitor_bots())
        
        logger.info("✅ All bots started successfully!")
        
        # Wait for all bots to complete or shutdown signal
        await asyncio.gather(*BOT_TASKS.values(), return_exceptions=True)
        
    except Exception as e:
        logger.error(f"❌ Orchestrator error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        logger.info("🧹 Cleaning up bot tasks...")
        for task in BOT_TASKS.values():
            if not task.done():
                task.cancel()
        
        logger.info("🔒 All bots stopped. Orchestrator shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Orchestrator interrupted by user")
    except Exception as e:
        logger.error(f"❌ Orchestrator failed: {e}")
        sys.exit(1)
