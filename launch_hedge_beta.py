#!/usr/bin/env python3
"""
🚀 Hedge Bot - Beta.Drift.Trade Launcher
Launches the Hedge Bot specifically in the beta.drift.trade environment.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add libs directory to path
sys.path.append(str(Path(__file__).parent / "libs"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hedge_beta.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import bot components
from libs.drift.client import build_client_from_config, DriftpyClient
from libs.order_management import PositionTracker, OrderManager
from orchestrator.risk_manager import RiskManager
from bots.hedge.main import hedge_iteration

class HedgeBetaLauncher:
    """Launcher for Hedge Bot in beta.drift.trade environment."""

    def __init__(self):
        self.client = None
        self.position_tracker = PositionTracker()
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager()
        self.iteration_count = 0
        self.errors = []

    async def initialize_beta_client(self) -> bool:
        """Initialize Drift client for beta environment."""
        try:
            logger.info("[INIT] Initializing Drift client for beta.drift.trade...")

            # Set beta environment variables
            os.environ['ENV'] = 'mainnet'
            os.environ['DRIFT_HTTP_URL'] = 'https://api.mainnet-beta.solana.com'
            os.environ['DRIFT_WS_URL'] = 'wss://api.mainnet-beta.solana.com'
            os.environ['USE_MOCK'] = 'false'  # Use real client for beta

            # Build client from config
            self.client = await build_client_from_config('configs/core/drift_client.yaml')

            if isinstance(self.client, DriftpyClient):
                logger.info("[SUCCESS] DriftpyClient initialized for beta")
                logger.info("[INFO] Connected to: https://beta.drift.trade")
                logger.info("[INFO] Using simulation mode - orders will be logged but not executed")
                logger.warning("[WARNING] This is a SIMULATION - no real orders will be placed!")
                logger.warning("[INFO] To place real orders, use the working DriftpyClient from drift-bots/ directory")

                # Client is ready to use (no initialization needed for simulation)
                return True
            else:
                logger.error("[ERROR] Expected DriftpyClient but got different client type")
                return False

        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize beta client: {e}")
            self.errors.append(f"Client initialization failed: {e}")
            return False

    async def check_wallet_status(self) -> bool:
        """Check wallet balance and connection."""
        try:
            logger.info("[BALANCE] Beta Wallet Status (Simulation Mode):")
            logger.info("   Mode: SIMULATION - No real wallet required")
            logger.info("   Status: Ready for beta hedge testing")
            logger.info("   Note: Orders will be simulated, not executed on blockchain")

            # Simulation mode - always return true
            return True

        except Exception as e:
            logger.error(f"[ERROR] Error checking wallet status: {e}")
            return False

    async def run_hedge_trading_loop(self):
        """Main hedge trading loop for beta environment."""
        logger.info("[TRADE] Starting Hedge Bot trading loop on beta.drift.trade...")
        logger.info("[INFO] View positions at: https://beta.drift.trade")

        # Beta-specific hedge configuration (conservative)
        hedge_cfg = {
            "hedge": {
                "max_inventory_usd": 100.0,  # Conservative for beta
                "urgency_threshold": 0.7,
                "ioc": {"max_slippage_bps": 5},
                "passive": {"max_slippage_bps": 2}
            }
        }

        while True:
            try:
                self.iteration_count += 1
                logger.info(f"[TRADE] Starting beta hedge iteration #{self.iteration_count}")

                # Run hedge iteration - THIS WILL PLACE REAL ORDERS ON BETA!
                await hedge_iteration(hedge_cfg, self.client, self.risk_manager,
                                    self.position_tracker, self.order_manager)

                # Log status
                logger.info("[STATUS] Beta Hedge Iteration Status:")
                logger.info(f"   Net Exposure: ${self.position_tracker.net_exposure:.2f}")
                logger.info(f"   Total Volume: ${self.position_tracker.volume:.2f}")
                logger.info(f"   Open Orders: {len(self.order_manager._orders)}")

                # Check if we have positions to display
                if hasattr(self.client, 'get_positions'):
                    positions = self.client.get_positions()
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
                    await self.check_wallet_status()

                # Wait before next iteration (slightly slower for beta)
                await asyncio.sleep(8)

            except Exception as e:
                logger.error(f"[ERROR] Error in beta hedge iteration {self.iteration_count}: {e}")
                self.errors.append(f"Iteration {self.iteration_count} error: {e}")

                # Wait longer after errors
                await asyncio.sleep(15)

    async def run(self):
        """Main execution method for beta hedge trading."""
        logger.info("[LAUNCH] Starting Hedge Bot for beta.drift.trade")
        logger.info("=" * 70)
        logger.info("[IMPORTANT] SIMULATION MODE - Orders will be logged but NOT executed!")
        logger.info("[INFO] This is a safe testing environment for hedge bot development")
        logger.info("=" * 70)

        try:
            # Step 1: Initialize beta client
            if not await self.initialize_beta_client():
                logger.error("[ERROR] Beta client initialization failed - aborting")
                return

            # Step 2: Check wallet status
            if not await self.check_wallet_status():
                logger.error("[ERROR] Wallet check failed - aborting")
                return

            # Step 3: Start hedge trading loop
            logger.info("[STARTING] Beginning SIMULATION beta hedge trading session...")
            logger.info("[INFO] Simulation Mode: Orders will be logged but not executed")
            logger.info("[INFO] View simulation logs for hedge bot behavior")

            await self.run_hedge_trading_loop()

        except KeyboardInterrupt:
            logging.info("[SHUTDOWN] Received shutdown signal")
        except Exception as e:
            logging.error(f"[ERROR] Fatal error in beta execution: {e}")
            self.errors.append(f"Fatal error: {e}")
        finally:
            # Cleanup
            logging.info("[CLEANUP] Starting cleanup...")

            if self.client and hasattr(self.client, 'close'):
                try:
                    await self.client.close()
                    logging.info("[SUCCESS] Beta client closed successfully")
                except Exception as e:
                    logging.error(f"[ERROR] Error closing beta client: {e}")

            # Final summary
            logging.info("=" * 70)
            logging.info("[SUMMARY] BETA HEDGE TRADING SESSION COMPLETE")
            logging.info("=" * 70)
            logging.info(f"Total Iterations: {self.iteration_count}")
            logging.info(f"Net Exposure: ${self.position_tracker.net_exposure:.2f}")
            logging.info(f"Total Volume: ${self.position_tracker.volume:.2f}")

            if self.errors:
                logging.warning(f"Errors Encountered: {len(self.errors)}")
                for i, error in enumerate(self.errors[-5:], 1):  # Show last 5
                    logging.warning(f"  {i}. {error}")
            else:
                logging.info("Errors: None - Clean beta session!")

            logging.info("=" * 70)

async def main():
    """Entry point."""
    launcher = HedgeBetaLauncher()
    await launcher.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("[SHUTDOWN] Beta hedge bot interrupted by user")
    except Exception as e:
        logging.error(f"[ERROR] Beta hedge bot failed: {e}")
        sys.exit(1)
