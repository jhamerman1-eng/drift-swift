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

# Import bot components FIRST (main project)
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "libs"))
sys.path.insert(0, str(project_root / "orchestrator"))
sys.path.insert(0, str(project_root / "bots"))

# Import the main Drift client with multi-format wallet support
from libs.drift.client import DriftpyClient

from libs.order_management import PositionTracker, OrderManager
from orchestrator.risk_manager import RiskManager
from bots.hedge.main import hedge_iteration

class RealHedgeBetaLauncher:
    """Launcher for REAL Hedge Bot trading on beta.drift.trade."""

    def __init__(self, config_path: str = "configs/core/drift_client.yaml"):
        self.trader = None
        self.position_tracker = PositionTracker()
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager()
        self.iteration_count = 0
        self.errors = []
        self.config_path = config_path

        # Load configuration from file or use defaults
        self._load_config()

    def _load_config(self):
        """Load configuration from file or use defaults."""
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Extract configuration values
            self.rpc_url = config.get('rpc', {}).get('http_url', "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")
            self.wallet_path = config.get('wallets', {}).get('maker_keypair_path', ".beta_dev_wallet.json")
            self.env = config.get('cluster', 'devnet')

        except (FileNotFoundError, yaml.YAMLError, KeyError):
            # Fallback to hardcoded defaults if config file not found or invalid
            logger.warning(f"[CONFIG] Could not load {self.config_path}, using defaults")
            self.rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
            self.wallet_path = ".beta_dev_wallet.json"
            self.env = "devnet"

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

            # Load wallet with multi-format support (like main client)
            import json
            import os

            with open(self.wallet_path, 'r') as f:
                content = f.read().strip()

            # Handle different wallet formats (same logic as main client)
            try:
                wallet_data = json.loads(content)
                if isinstance(wallet_data, dict) and 'secret_key' in wallet_data:
                    # New format: {"public_key": "...", "secret_key": "..."}
                    secret_key = wallet_data['secret_key']
                elif isinstance(wallet_data, list) and len(wallet_data) >= 64:
                    # Old format: [174,47,154,16,...]
                    from base58 import b58encode
                    secret_bytes = bytes(wallet_data[:64])
                    secret_key = b58encode(secret_bytes).decode('utf-8')
                else:
                    raise ValueError("Invalid wallet format")
            except (json.JSONDecodeError, ValueError):
                # Raw base58 string format
                secret_key = content.strip()

            # Initialize the REAL trader using main client
            ws_url = self.rpc_url.replace("https://", "wss://")

            self.trader = DriftpyClient(
                rpc_url=self.rpc_url,
                wallet_secret_key=secret_key,  # Now contains the actual secret key
                market="SOL-PERP",  # Default market for hedge bot
                ws_url=ws_url,
                use_fallback=True
            )

            logger.info("[SUCCESS] REAL Drift client initialized and ready for beta trading!")
            logger.info("[SUCCESS] Connected to beta.drift.trade - READY FOR REAL ORDERS!")
            return True

        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize real beta client: {e}")
            self.errors.append(f"Real client initialization failed: {e}")
            return False

    async def check_wallet_and_balance(self) -> bool:
        """Check wallet balance for beta trading."""
        try:
            logger.info("[BALANCE] Checking wallet balance for beta trading...")

            # Use the trader's balance checking method if available
            if hasattr(self.trader, 'check_wallet_balance'):
                balance_info = await self.trader.check_wallet_balance()
                if balance_info:
                    logger.info("[SUCCESS] Wallet balance verified for beta trading")
                    return True
                else:
                    logger.error("[ERROR] Insufficient balance for beta trading")
                    logger.info("[INFO] Get devnet SOL from: https://faucet.solana.com")
                    return False
            else:
                # Main client doesn't have balance checking - just verify wallet was loaded
                logger.info("[INFO] Main client initialized - wallet loaded successfully")
                logger.info("[INFO] Make sure your wallet has sufficient SOL for gas fees")
                return True

        except Exception as e:
            logger.error(f"[ERROR] Error checking wallet balance: {e}")
            logger.warning("[WARNING] Proceeding without balance verification due to error")
            return True

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
                try:
                    if hasattr(self.trader, 'get_positions'):
                        positions = self.trader.get_positions()  # Main client returns Dict[str, Position]
                        if positions:
                            logger.info(f"   Active Positions: {len(positions)}")
                            for market, pos in positions.items():
                                logger.info(f"      {market}: {pos.size:.4f} @ ${pos.avg_price:.4f}")
                        else:
                            logger.info("   Active Positions: None")
                    else:
                        logger.info("   Active Positions: Method not available")
                except Exception as e:
                    logger.debug(f"Could not get positions: {e}")
                    logger.info("   Active Positions: Error retrieving")

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
