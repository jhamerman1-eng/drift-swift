#!/usr/bin/env python3
"""
🚀 DEV TRADING LAUNCH SCRIPT
Launches Hedge Bot on Drift Devnet with comprehensive error logging and monitoring.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
import json
from typing import Dict, Any

# Add libs directory to path
sys.path.append(str(Path(__file__).parent / "libs"))

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dev_trading_launch.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Import bot components
from libs.drift.client import build_client_from_config, DriftpyClient
from libs.order_management import PositionTracker, OrderManager
from orchestrator.risk_manager import RiskManager
from bots.hedge.main import hedge_iteration

class DevTradingLauncher:
    """Manages launching and monitoring the hedge bot on devnet."""

    def __init__(self):
        self.client = None
        self.position_tracker = PositionTracker()
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager()
        self.iteration_count = 0
        self.errors = []

    async def initialize_client(self) -> bool:
        """Initialize Drift client with proper error handling."""
        try:
            logging.info("[INIT] Initializing Drift client for devnet trading...")

            # Build client from config
            self.client = await build_client_from_config('configs/core/drift_client.yaml')

            if isinstance(self.client, DriftpyClient):
                logging.info("[SUCCESS] Real DriftpyClient initialized successfully")

                # Initialize the client (add user account, subscribe)
                init_success = await self.client.initialize()
                if init_success:
                    logging.info("[SUCCESS] Client fully initialized and ready for trading")
                    return True
                else:
                    logging.warning("[WARNING] Client initialization completed with warnings")
                    return True
            else:
                logging.error("[ERROR] Expected DriftpyClient but got different client type")
                return False

        except Exception as e:
            logging.error(f"[ERROR] Failed to initialize client: {e}")
            self.errors.append(f"Client initialization failed: {e}")
            return False

    async def check_wallet_balance(self) -> float:
        """Check wallet balance and log funding requirements."""
        try:
            if not hasattr(self.client, 'solana_client') or not self.client.solana_client:
                logging.warning("[WARNING] Cannot check balance - no Solana client available")
                return 0.0

            if not hasattr(self.client, 'keypair'):
                logging.warning("[WARNING] Cannot check balance - no wallet keypair available")
                return 0.0

            balance = await self.client.solana_client.get_balance(self.client.keypair.pubkey())
            balance_sol = balance.value / 1e9

            logging.info(f"[BALANCE] Wallet Balance: {balance_sol:.4f} SOL")
            if balance_sol < 0.1:
                logging.warning("[WARNING] LOW BALANCE - Consider funding wallet for trading")
                logging.warning("[INFO] Use: https://faucet.solana.com")
                logging.warning(f"   Address: {self.client.keypair.pubkey()}")

            return balance_sol

        except Exception as e:
            logging.error(f"[ERROR] Error checking balance: {e}")
            return 0.0

    async def run_trading_loop(self):
        """Main trading loop with error handling and monitoring."""
        logging.info("[TRADE] Starting devnet trading loop...")

        hedge_cfg = {
            "hedge": {
                "max_inventory_usd": 1000,  # Smaller for devnet testing
                "urgency_threshold": 0.7,
                "ioc": {"max_slippage_bps": 5},
                "passive": {"max_slippage_bps": 2}
            }
        }

        while True:
            try:
                self.iteration_count += 1
                logging.info(f"[TRADE] Starting iteration #{self.iteration_count}")

                # Run hedge iteration
                await hedge_iteration(hedge_cfg, self.client, self.risk_manager,
                                    self.position_tracker, self.order_manager)

                # Log status
                logging.info("[STATUS] Iteration Status:")
                logging.info(f"   Net Exposure: ${self.position_tracker.net_exposure:.2f}")
                logging.info(f"   Total Volume: ${self.position_tracker.volume:.2f}")
                logging.info(f"   Open Orders: {len(self.order_manager._orders)}")
                risk_state = self.risk_manager.evaluate(self.position_tracker.net_exposure)
                logging.info(f"   Risk State: Drawdown {risk_state.drawdown_pct:.2f}%")

                # Check balance periodically
                if self.iteration_count % 5 == 0:
                    await self.check_wallet_balance()

                # Wait before next iteration
                await asyncio.sleep(3)

            except Exception as e:
                logging.error(f"[ERROR] Error in trading loop iteration {self.iteration_count}: {e}")
                self.errors.append(f"Iteration {self.iteration_count} error: {e}")

                # Wait longer after errors
                await asyncio.sleep(5)

    async def monitor_and_log(self):
        """Monitor bot performance and log comprehensive stats."""
        while True:
            try:
                await asyncio.sleep(30)  # Log every 30 seconds

                if hasattr(self.client, 'stats'):
                    stats = self.client.stats.get_summary()
                    logging.info("[STATS] Performance Stats:")
                    for key, value in stats.items():
                        logging.info(f"   {key}: {value}")

                # Log any accumulated errors
                if self.errors:
                    logging.warning(f"[ERRORS] Accumulated {len(self.errors)} errors:")
                    for i, error in enumerate(self.errors[-5:], 1):  # Show last 5
                        logging.warning(f"   {i}. {error}")

            except Exception as e:
                logging.error(f"[ERROR] Error in monitoring: {e}")

    async def run(self):
        """Main execution method."""
        logging.info("[LAUNCH] Starting DEV Trading Launch Sequence")
        logging.info("=" * 60)

        try:
            # Step 1: Initialize client
            if not await self.initialize_client():
                logging.error("[ERROR] Client initialization failed - aborting")
                return

            # Step 2: Check balance
            balance = await self.check_wallet_balance()

            # Step 3: Start monitoring task
            monitor_task = asyncio.create_task(self.monitor_and_log())

            # Step 4: Start trading loop
            await self.run_trading_loop()

        except KeyboardInterrupt:
            logging.info("[SHUTDOWN] Received shutdown signal")
        except Exception as e:
            logging.error(f"[ERROR] Fatal error in main execution: {e}")
            self.errors.append(f"Fatal error: {e}")
        finally:
            # Cleanup
            logging.info("[CLEANUP] Starting cleanup...")

            if self.client and hasattr(self.client, 'close'):
                try:
                    await self.client.close()
                    logging.info("[SUCCESS] Client closed successfully")
                except Exception as e:
                    logging.error(f"[ERROR] Error closing client: {e}")

            # Final error summary
            if self.errors:
                logging.warning("[ERRORS] FINAL ERROR SUMMARY:")
                for i, error in enumerate(self.errors, 1):
                    logging.warning(f"   {i}. {error}")
                logging.warning(f"Total errors: {len(self.errors)}")
            else:
                logging.info("[SUCCESS] No errors recorded during session")

            logging.info("[COMPLETE] Dev trading session completed")
            logging.info("=" * 60)

async def main():
    """Entry point."""
    launcher = DevTradingLauncher()
    await launcher.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("[SHUTDOWN] Launch script interrupted by user")
    except Exception as e:
        logging.error(f"[ERROR] Launch script failed: {e}")
        sys.exit(1)
