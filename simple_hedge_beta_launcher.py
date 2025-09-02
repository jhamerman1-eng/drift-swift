#!/usr/bin/env python3
"""
🚀 Simple Hedge Bot - Beta.Drift.Trade Launcher
Places REAL orders on beta.drift.trade using working components
"""

import asyncio
import logging
import sys
import os
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_hedge_beta.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def run_trading_loop(trader, project_root):
    """Async trading loop for beta hedge bot"""

    # Initialize the trader
    logger.info("[INIT] Connecting to beta.drift.trade...")
    init_success = await trader.initialize()
    if not init_success:
        logger.error("[ERROR] Failed to initialize Drift client")
        return

    logger.info("[SUCCESS] Connected to beta.drift.trade - READY FOR REAL ORDERS!")

    # Check wallet balance
    logger.info("[BALANCE] Checking wallet balance...")
    balance_ok = await trader.check_wallet_balance()
    if not balance_ok:
        logger.error("[ERROR] Insufficient balance for beta trading")
        logger.info("[INFO] Get devnet SOL from: https://faucet.solana.com")
        return

    # Initialize bot components
    position_tracker = PositionTracker()
    order_manager = OrderManager()
    risk_manager = RiskManager()

    # Beta configuration
    hedge_cfg = {
        "hedge": {
            "max_inventory_usd": 50.0,
            "urgency_threshold": 0.8,
            "ioc": {"max_slippage_bps": 5},
            "passive": {"max_slippage_bps": 3}
        }
    }

    logger.info("[STARTING] Beginning REAL beta hedge trading session...")
    logger.warning("[FINAL WARNING] REAL ORDERS WILL BE PLACED NOW!")

    iteration_count = 0
    while True:
        try:
            iteration_count += 1
            logger.info(f"[TRADE] Starting REAL beta hedge iteration #{iteration_count}")

            # Run hedge iteration - THIS WILL PLACE REAL ORDERS!
            await hedge_iteration(hedge_cfg, trader, risk_manager,
                                position_tracker, order_manager)

            # Log status
            logger.info("[STATUS] REAL Beta Hedge Iteration Status:")
            logger.info(f"   Net Exposure: ${position_tracker.net_exposure:.2f}")
            logger.info(f"   Total Volume: ${position_tracker.volume:.2f}")
            logger.info(f"   Open Orders: {len(order_manager._orders)}")

            risk_state = risk_manager.evaluate(position_tracker.net_exposure)
            logger.info(f"   Risk State: Drawdown {risk_state.drawdown_pct:.2f}%")

            # Wait before next iteration
            await asyncio.sleep(10)

        except KeyboardInterrupt:
            logger.info("[SHUTDOWN] Received shutdown signal")
            break
        except Exception as e:
            logger.error(f"[ERROR] Error in beta hedge iteration {iteration_count}: {e}")
            await asyncio.sleep(20)

def main():
    """Simple hedge bot launcher for beta.drift.trade"""
    logger.info("[LAUNCH] Starting Simple Hedge Bot for beta.drift.trade")
    logger.warning("[WARNING] This will place REAL orders on beta.drift.trade!")
    logger.info("=" * 70)

    try:
        # Import working components from drift-bots directory
        project_root = Path(__file__).parent
        drift_bots_path = project_root / "drift-bots"

        # Add paths to sys.path
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(drift_bots_path))

        logger.info("[INIT] Importing working DriftPy client...")
        from place_real_trade_final import RealDriftTrader
        logger.info("[SUCCESS] DriftPy client imported successfully")

        logger.info("[INIT] Importing bot components...")
        # Import from main project libs, not drift-bots libs
        sys.path.insert(0, str(project_root / "libs"))
        sys.path.insert(0, str(project_root / "orchestrator"))
        sys.path.insert(0, str(project_root / "bots"))

        from libs.order_management import PositionTracker, OrderManager
        from orchestrator.risk_manager import RiskManager
        from bots.hedge.main import hedge_iteration
        logger.info("[SUCCESS] All bot components imported successfully")

        # Check if wallet exists
        wallet_path = project_root / ".beta_dev_wallet.json"
        if not wallet_path.exists():
            logger.error(f"[ERROR] Wallet not found: {wallet_path}")
            logger.info("[INFO] Please run: python setup_beta_wallet.py")
            return

        # Initialize trader
        trader = RealDriftTrader(
            rpc_url="https://api.mainnet-beta.solana.com",
            wallet_path=str(wallet_path),
            env="devnet"
        )

        # Run the async trading loop
        asyncio.run(run_trading_loop(trader, project_root))

    except KeyboardInterrupt:
        logging.info("[SHUTDOWN] Beta hedge bot interrupted by user")
    except Exception as e:
        logging.error(f"[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("=" * 70)
        logger.info("[SUMMARY] BETA HEDGE TRADING SESSION COMPLETE")
        logger.info("=" * 70)

if __name__ == "__main__":
    main()
