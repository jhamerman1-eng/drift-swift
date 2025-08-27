#!/usr/bin/env python3
"""
🚀 REAL TRADING LAUNCH SCRIPT
Launches Hedge Bot for LIVE trading on Drift Protocol devnet with wallet funding check
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
        logging.FileHandler('real_trading_launch.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Import bot components
from libs.drift.client import build_client_from_config, DriftpyClient
from libs.order_management import PositionTracker, OrderManager
from orchestrator.risk_manager import RiskManager
from bots.hedge.main import hedge_iteration

class RealTradingLauncher:
    """Manages launching and monitoring the hedge bot for REAL trading."""

    def __init__(self):
        self.client = None
        self.position_tracker = PositionTracker()
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager()
        self.iteration_count = 0
        self.errors = []
        self.wallet_address = None

    async def wait_for_funding(self, required_balance: float = 0.1) -> bool:
        """Wait for wallet to be funded with sufficient SOL."""
        logging.info("[FUNDING] Checking wallet balance...")

        if not hasattr(self.client, 'solana_client') or not self.client.solana_client:
            logging.error("[ERROR] No Solana client available")
            return False

        if not hasattr(self.client, 'keypair'):
            logging.error("[ERROR] No wallet keypair available")
            return False

        self.wallet_address = str(self.client.keypair.pubkey())

        while True:
            try:
                balance = await self.client.solana_client.get_balance(self.client.keypair.pubkey())
                balance_sol = balance.value / 1e9

                logging.info(f"[BALANCE] Current Balance: {balance_sol:.4f} SOL")
                if balance_sol >= required_balance:
                    logging.info("[SUCCESS] Sufficient balance detected - starting real trading!")
                    return True
                else:
                    logging.info(f"[WAITING] Current Balance: {balance_sol:.4f} SOL (need {required_balance:.4f} SOL)")
                    logging.info("[WAITING] Please fund the wallet and press Enter to continue...")
                    logging.info(f"[INFO] Wallet Address: {self.wallet_address}")
                    logging.info("[INFO] Funding: https://faucet.solana.com (Devnet)")

                    # Wait for user input or check again in 10 seconds
                    try:
                        await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(None, input),
                            timeout=10.0
                        )
                    except asyncio.TimeoutError:
                        logging.info("[WAITING] No input received, checking balance again...")

            except Exception as e:
                logging.error(f"[ERROR] Error checking balance: {e}")
                await asyncio.sleep(5)

    async def run_real_trading_loop(self):
        """Main REAL trading loop with live order placement."""
        logging.info("[TRADING] Starting REAL trading loop on Drift Protocol!")

        hedge_cfg = {
            "hedge": {
                "max_inventory_usd": 1000,  # Conservative for devnet testing
                "urgency_threshold": 0.7,
                "ioc": {"max_slippage_bps": 5},
                "passive": {"max_slippage_bps": 2}
            }
        }

        while True:
            try:
                self.iteration_count += 1
                logging.info(f"[TRADING] Starting iteration #{self.iteration_count}")

                # Run hedge iteration - THIS WILL PLACE REAL ORDERS!
                await hedge_iteration(hedge_cfg, self.client, self.risk_manager,
                                    self.position_tracker, self.order_manager)

                # Log status
                logging.info("[STATUS] Iteration Status:")
                logging.info(f"   Net Exposure: ${self.position_tracker.net_exposure:.2f}")
                logging.info(f"   Total Volume: ${self.position_tracker.volume:.2f}")
                logging.info(f"   Open Orders: {len(self.order_manager._orders)}")

                # Check if we have positions to display
                if hasattr(self.client, 'get_positions'):
                    positions = self.client.get_positions()
                    if positions:
                        logging.info(f"   Active Positions: {len(positions)}")
                        for pos in positions:
                            logging.info(f"      {pos.market}: {pos.size:.4f} @ ${pos.avg_price:.4f}")
                    else:
                        logging.info("   Active Positions: None")

                risk_state = self.risk_manager.evaluate(self.position_tracker.net_exposure)
                logging.info(f"   Risk State: Drawdown {risk_state.drawdown_pct:.2f}%")

                # Check balance every 10 iterations
                if self.iteration_count % 10 == 0:
                    await self.check_wallet_balance()

                # Wait before next iteration
                await asyncio.sleep(5)  # Slightly faster for real trading

            except Exception as e:
                logging.error(f"[ERROR] Error in trading loop iteration {self.iteration_count}: {e}")
                self.errors.append(f"Iteration {self.iteration_count} error: {e}")

                # Wait longer after errors
                await asyncio.sleep(10)

    async def check_wallet_balance(self) -> float:
        """Check wallet balance during trading."""
        try:
            if not hasattr(self.client, 'solana_client') or not self.client.solana_client:
                return 0.0

            if not hasattr(self.client, 'keypair'):
                return 0.0

            balance = await self.client.solana_client.get_balance(self.client.keypair.pubkey())
            balance_sol = balance.value / 1e9

            logging.info(f"[BALANCE] Current Balance: {balance_sol:.4f} SOL")
            if balance_sol < 0.01:
                logging.warning("[WARNING] LOW BALANCE - Consider adding more SOL")

            return balance_sol

        except Exception as e:
            logging.error(f"[ERROR] Error checking balance: {e}")
            return 0.0

    async def initialize_client(self) -> bool:
        """Initialize Drift client for real trading."""
        try:
            logging.info("[INIT] Initializing Drift client for REAL trading...")

            # Build client from config
            self.client = await build_client_from_config('configs/core/drift_client.yaml')

            if isinstance(self.client, DriftpyClient):
                logging.info("[SUCCESS] Real DriftpyClient initialized successfully")

                # Initialize the client (add user account, subscribe)
                init_success = await self.client.initialize()
                if init_success:
                    logging.info("[SUCCESS] Client fully initialized and ready for REAL trading!")
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

    async def run(self):
        """Main execution method for real trading."""
        logging.info("[LAUNCH] Starting REAL TRADING Launch Sequence")
        logging.info("=" * 70)
        logging.info("[IMPORTANT] This will place REAL orders on Drift Protocol devnet!")
        logging.info("=" * 70)

        try:
            # Step 1: Initialize client
            if not await self.initialize_client():
                logging.error("[ERROR] Client initialization failed - aborting")
                return

            # Step 2: Wait for funding
            if not await self.wait_for_funding():
                logging.error("[ERROR] Funding check failed - aborting")
                return

            # Step 3: Start trading loop
            logging.info("[STARTING] Beginning REAL trading session...")
            logging.info(f"[INFO] Wallet: {self.wallet_address}")
            logging.info("[INFO] View trades on: https://beta.drift.trade (devnet)")

            await self.run_real_trading_loop()

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

            # Final summary
            logging.info("=" * 70)
            logging.info("[SUMMARY] REAL TRADING SESSION COMPLETE")
            logging.info("=" * 70)
            logging.info(f"Total Iterations: {self.iteration_count}")
            logging.info(f"Net Exposure: ${self.position_tracker.net_exposure:.2f}")
            logging.info(f"Total Volume: ${self.position_tracker.volume:.2f}")

            if self.errors:
                logging.warning(f"Errors Encountered: {len(self.errors)}")
                for i, error in enumerate(self.errors[-5:], 1):  # Show last 5
                    logging.warning(f"  {i}. {error}")
            else:
                logging.info("Errors: None - Clean session!")

            logging.info("=" * 70)

async def main():
    """Entry point."""
    launcher = RealTradingLauncher()
    await launcher.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("[SHUTDOWN] Real trading launch interrupted by user")
    except Exception as e:
        logging.error(f"[ERROR] Real trading launch failed: {e}")
        sys.exit(1)
