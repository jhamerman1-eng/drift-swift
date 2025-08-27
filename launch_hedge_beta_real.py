#!/usr/bin/env python3
"""
🚀 REAL Hedge Bot - Beta.Drift.Trade Launcher
Places REAL orders on beta.drift.trade (no simulation!)
"""

import asyncio
import logging
import sys
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Add drift-bots directory to path for working DriftPy implementation
sys.path.append(str(Path(__file__).parent / "drift-bots"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hedge_beta_real.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import the WORKING DriftPy implementation
from place_real_trade_final import RealDriftTrader

# Import bot components
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "libs"))
sys.path.insert(0, str(project_root / "orchestrator"))
sys.path.insert(0, str(project_root / "bots"))

from libs.order_management import PositionTracker, OrderManager
from orchestrator.risk_manager import RiskManager
from bots.hedge.main import hedge_iteration

class RealHedgeBetaLauncher:
    """Launcher for REAL Hedge Bot trading on beta.drift.trade."""

    def __init__(self):
        self.trader = None
        self.position_tracker = PositionTracker()
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager()
        self.iteration_count = 0
        self.errors = []

        # Beta environment configuration
        self.rpc_url = "https://api.mainnet-beta.solana.com"
        self.wallet_path = ".beta_dev_wallet.json"  # User needs to create this
        self.env = "devnet"  # Use devnet for beta testing

    async def initialize_real_beta_client(self) -> bool:
        """Initialize REAL Drift client for beta environment."""
        try:
            logger.info("[INIT] Initializing REAL Drift client for beta.drift.trade...")
            logger.warning("[WARNING] This will place REAL orders on beta.drift.trade!")
            logger.info(f"[CONFIG] RPC: {self.rpc_url}")
            logger.info(f"[CONFIG] Wallet: {self.wallet_path}")
            logger.info(f"[CONFIG] Environment: {self.env}")

            # Check if wallet exists
            if not Path(self.wallet_path).exists():
                logger.error(f"[ERROR] Wallet file not found: {self.wallet_path}")
                logger.info("[INFO] Create wallet with: solana-keygen new --outfile .beta_dev_wallet.json")
                logger.info("[INFO] Fund with devnet SOL from: https://faucet.solana.com")
                return False

            # Initialize the REAL trader
            self.trader = RealDriftTrader(
                rpc_url=self.rpc_url,
                wallet_path=self.wallet_path,
                env=self.env
            )

            # Initialize the trader (connects to Drift Protocol)
            init_success = await self.trader.initialize()
            if init_success:
                logger.info("[SUCCESS] REAL Drift client initialized and ready for beta trading!")
                logger.info("[SUCCESS] Connected to beta.drift.trade - READY FOR REAL ORDERS!")
                return True
            else:
                logger.error("[ERROR] REAL Drift client initialization failed")
                return False

        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize real beta client: {e}")
            self.errors.append(f"Real client initialization failed: {e}")
            return False

    async def check_wallet_and_balance(self) -> bool:
        """Check wallet balance for beta trading."""
        try:
            logger.info("[BALANCE] Checking wallet balance for beta trading...")

            # Use the trader's balance checking method
            balance_info = await self.trader.check_wallet_balance()
            if balance_info:
                logger.info("[SUCCESS] Wallet balance verified for beta trading")
                return True
            else:
                logger.error("[ERROR] Insufficient balance for beta trading")
                logger.info("[INFO] Get devnet SOL from: https://faucet.solana.com")
                return False

        except Exception as e:
            logger.error(f"[ERROR] Error checking wallet balance: {e}")
            return False

    async def run_real_hedge_trading_loop(self):
        """Main REAL hedge trading loop for beta environment."""
        logger.info("[TRADE] Starting REAL hedge trading loop on beta.drift.trade...")
        logger.warning("[WARNING] This will place REAL ORDERS - Monitor closely!")
        logger.info("[INFO] View positions at: https://beta.drift.trade")

        # Beta-specific hedge configuration (conservative for real trading)
        hedge_cfg = {
            "hedge": {
                "max_inventory_usd": 50.0,  # Conservative for beta real trading
                "urgency_threshold": 0.8,
                "ioc": {"max_slippage_bps": 5},
                "passive": {"max_slippage_bps": 3}
            }
        }

        while True:
            try:
                self.iteration_count += 1
                logger.info(f"[TRADE] Starting REAL beta hedge iteration #{self.iteration_count}")

                # Run hedge iteration - THIS WILL PLACE REAL ORDERS ON BETA!
                await hedge_iteration(hedge_cfg, self.trader, self.risk_manager,
                                    self.position_tracker, self.order_manager)

                # Log status
                logger.info("[STATUS] REAL Beta Hedge Iteration Status:")
                logger.info(f"   Net Exposure: ${self.position_tracker.net_exposure:.2f}")
                logger.info(f"   Total Volume: ${self.position_tracker.volume:.2f}")
                logger.info(f"   Open Orders: {len(self.order_manager._orders)}")

                # Check positions using real trader
                if hasattr(self.trader, 'get_positions'):
                    positions = await self.trader.get_positions()
                    if positions:
                        logger.info(f"   Active Positions: {len(positions)}")
                        for pos in positions:
                            logger.info(f"      {pos.market}: {pos.size:.4f} @ ${pos.avg_price:.4f}")
                    else:
                        logger.info("   Active Positions: None")

                risk_state = self.risk_manager.evaluate(self.position_tracker.net_exposure)
                logger.info(f"   Risk State: Drawdown {risk_state.drawdown_pct:.2f}%")

                # Check balance every 5 iterations
                if self.iteration_count % 5 == 0:
                    await self.check_wallet_and_balance()

                # Wait before next iteration (conservative timing for real trading)
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"[ERROR] Error in REAL beta hedge iteration {self.iteration_count}: {e}")
                self.errors.append(f"Iteration {self.iteration_count} error: {e}")

                # Wait longer after errors
                await asyncio.sleep(20)

    async def run(self):
        """Main execution method for REAL beta hedge trading."""
        logger.info("[LAUNCH] Starting REAL Hedge Bot for beta.drift.trade")
        logger.info("=" * 70)
        logger.warning("[CRITICAL] THIS WILL PLACE REAL ORDERS ON BETA.DRIFT.TRADE!")
        logger.warning("[CRITICAL] Make sure you have funded your wallet!")
        logger.info("=" * 70)

        try:
            # Step 1: Initialize REAL beta client
            if not await self.initialize_real_beta_client():
                logger.error("[ERROR] REAL beta client initialization failed - aborting")
                return

            # Step 2: Check wallet and balance
            if not await self.check_wallet_and_balance():
                logger.error("[ERROR] Wallet/balance check failed - aborting")
                return

            # Step 3: Start REAL hedge trading loop
            logger.info("[STARTING] Beginning REAL beta hedge trading session...")
            logger.info(f"[INFO] Wallet: {self.wallet_path}")
            logger.info("[INFO] View trades on: https://beta.drift.trade")
            logger.warning("[FINAL WARNING] REAL ORDERS WILL BE PLACED NOW!")

            await self.run_real_hedge_trading_loop()

        except KeyboardInterrupt:
            logging.info("[SHUTDOWN] Received shutdown signal")
        except Exception as e:
            logging.error(f"[ERROR] Fatal error in REAL beta execution: {e}")
            self.errors.append(f"Fatal error: {e}")
        finally:
            # Cleanup
            logging.info("[CLEANUP] Starting cleanup...")

            if self.trader:
                try:
                    await self.trader.close()
                    logging.info("[SUCCESS] Real beta client closed successfully")
                except Exception as e:
                    logging.error(f"[ERROR] Error closing real beta client: {e}")

            # Final summary
            logging.info("=" * 70)
            logging.info("[SUMMARY] REAL BETA HEDGE TRADING SESSION COMPLETE")
            logging.info("=" * 70)
            logging.info(f"Total Iterations: {self.iteration_count}")
            logging.info(f"Net Exposure: ${self.position_tracker.net_exposure:.2f}")
            logging.info(f"Total Volume: ${self.position_tracker.volume:.2f}")

            if self.errors:
                logging.warning(f"Errors Encountered: {len(self.errors)}")
                for i, error in enumerate(self.errors[-5:], 1):  # Show last 5
                    logging.warning(f"  {i}. {error}")
            else:
                logging.info("Errors: None - Clean real beta session!")

            logging.info("=" * 70)

async def main():
    """Entry point."""
    launcher = RealHedgeBetaLauncher()
    await launcher.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("[SHUTDOWN] Real beta hedge bot interrupted by user")
    except Exception as e:
        logging.error(f"[ERROR] Real beta hedge bot failed: {e}")
        sys.exit(1)
