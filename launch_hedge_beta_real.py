#!/usr/bin/env python3
"""
REAL Hedge Bot launcher for beta.drift.trade (devnet/beta).
Places real test orders using the shared client builder and the
hedging iteration from bots/hedge/main.py.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

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

from libs.drift.client import build_client_from_config
from libs.order_management import PositionTracker, OrderManager, OrderRecord
from orchestrator.risk_manager import RiskManager
from bots.hedge.main import hedge_iteration


class RealHedgeBetaLauncher:
    """Launcher for REAL Hedge Bot trading on beta.drift.trade."""

    def __init__(self, config_path: str = "configs/core/drift_client.yaml", test_mode: bool = False):
        self.trader = None
        self.position_tracker = PositionTracker()
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager()
        self.iteration_count = 0
        self.errors: list[str] = []
        self.config_path = config_path
        self.test_mode = test_mode

        # Defaults
        self.rpc_url: Optional[str] = None
        self.wallet_path: str = ".beta_dev_wallet.json"
        self.env: str = "devnet"

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file or use defaults."""
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}

            self.rpc_url = (config.get('rpc', {}) or {}).get('http_url')
            self.wallet_path = (config.get('wallets', {}) or {}).get('maker_keypair_path', self.wallet_path)
            self.env = config.get('cluster', self.env)
        except Exception as e:
            logger.warning(f"[CONFIG] Could not load {self.config_path}: {e}; using defaults")

    async def initialize_real_beta_client(self) -> bool:
        """Initialize REAL Drift client using shared builder."""
        try:
            logger.info("[INIT] Initializing REAL Drift client for beta.drift.trade...")
            self.trader = await build_client_from_config(self.config_path)
            logger.info("[SUCCESS] Drift client initialized and ready for beta trading")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize shared client: {e}")
            return False

    async def check_wallet_and_balance(self) -> bool:
        """Basic readiness check; ensure client exists and remind about SOL."""
        try:
            logger.info("[BALANCE] Checking wallet readiness for beta trading...")
            if self.trader is not None:
                logger.info("[INFO] Client initialized. Ensure wallet has SOL for gas/fees.")
                return True
            logger.error("[ERROR] Trader client not initialized")
            return False
        except Exception as e:
            logger.error(f"[ERROR] Error during wallet check: {e}")
            return False

    async def run_simple_buy_sell_test(self) -> None:
        """Simple buy then sell to validate flow (5 minutes max)."""
        logger.info("[TEST] Starting SIMPLE BUY/SELL test on beta.drift.trade...")
        start_time = asyncio.get_event_loop().time()
        test_duration = 300  # 5 minutes

        try:
            market_index = 0  # SOL-PERP (typical)
            estimated_price = 100.0
            order_size = 0.01

            # BUY
            buy_price = estimated_price * 1.001
            logger.info(f"[TEST] Placing BUY {order_size} @ ~${buy_price:.2f}")
            buy_order = {
                "market_index": market_index,
                "side": "buy",
                "size": order_size,
                "price": buy_price,
                "order_type": "limit",
            }
            if self.trader is None:
                logger.error("[TEST] Trader client not initialized")
                return
            buy_order_id = await self.trader.place_order(buy_order)
            if buy_order_id:
                logger.info(f"[TEST] BUY placed. Signature: {buy_order_id}")
                self.order_manager.add_order(
                    OrderRecord(order_id=str(buy_order_id), side="buy", price=buy_price, size_usd=order_size * buy_price)
                )
            else:
                logger.error("[TEST] BUY order placement returned None")
                return

            # Wait 2 minutes
            await asyncio.sleep(120)

            # SELL
            sell_price = estimated_price * 0.999
            logger.info(f"[TEST] Placing SELL {order_size} @ ~${sell_price:.2f}")
            sell_order = {
                "market_index": market_index,
                "side": "sell",
                "size": order_size,
                "price": sell_price,
                "order_type": "limit",
            }
            sell_order_id = await self.trader.place_order(sell_order)
            if sell_order_id:
                logger.info(f"[TEST] SELL placed. Signature: {sell_order_id}")
                self.order_manager.add_order(
                    OrderRecord(order_id=str(sell_order_id), side="sell", price=sell_price, size_usd=order_size * sell_price)
                )
            else:
                logger.error("[TEST] SELL order placement returned None")

            # Wait remaining time
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining = max(0, test_duration - elapsed)
            if remaining > 0:
                logger.info(f"[TEST] Monitoring for {remaining:.0f}s...")
                await asyncio.sleep(remaining)

            logger.info("[TEST] Simple buy/sell test completed")
        except Exception as e:
            logger.error(f"[TEST] Error during simple test: {e}")
            import traceback
            traceback.print_exc()

    async def run_real_hedge_trading_loop(self) -> None:
        """Main REAL hedge trading loop for beta environment."""
        logger.info("[TRADE] Starting REAL hedge trading loop on beta.drift.trade...")

        hedge_cfg = {
            "hedge": {
                "max_inventory_usd": 50.0,
                "urgency_threshold": 0.8,
                "ioc": {"max_slippage_bps": 5},
                "passive": {"max_slippage_bps": 3},
            }
        }

        while True:
            try:
                self.iteration_count += 1
                if self.trader is not None:
                    await hedge_iteration(
                        hedge_cfg,
                        self.trader,
                        self.risk_manager,
                        self.position_tracker,
                        self.order_manager,
                    )
                else:
                    logger.error("[ERROR] Trader client is None, cannot run hedge_iteration")

                logger.info(
                    "[STATUS] net_exposure=$%.2f volume=$%.2f open_orders=%d",
                    self.position_tracker.net_exposure,
                    self.position_tracker.volume,
                    len(self.order_manager._orders),
                )

                if self.iteration_count % 5 == 0:
                    await self.check_wallet_and_balance()

                await asyncio.sleep(10)
            except Exception as e:
                logger.error(
                    f"[ERROR] Error in REAL beta hedge iteration {self.iteration_count}: {e}"
                )
                self.errors.append(f"Iteration {self.iteration_count} error: {e}")
                await asyncio.sleep(20)

    async def run(self) -> None:
        """Main execution method for REAL beta hedge trading."""
        logger.info("[LAUNCH] Starting REAL Hedge Bot for beta.drift.trade")
        logger.info("=" * 70)
        logger.warning("[CRITICAL] THIS WILL PLACE REAL ORDERS ON BETA.DRIFT.TRADE!")
        logger.info("=" * 70)

        try:
            if not await self.initialize_real_beta_client():
                logger.error("[ERROR] REAL beta client initialization failed - aborting")
                return

            if not await self.check_wallet_and_balance():
                logger.error("[ERROR] Wallet/balance check failed - aborting")
                return

            if self.test_mode:
                await self.run_simple_buy_sell_test()
            else:
                await self.run_real_hedge_trading_loop()
        finally:
            if self.trader:
                try:
                    await self.trader.close()
                    logger.info("[CLEANUP] Client closed")
                except Exception as e:
                    logger.error(f"[CLEANUP] Error closing client: {e}")


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="REAL Hedge Bot for beta.drift.trade")
    parser.add_argument("--test", action="store_true", help="Run simple buy/sell test instead of full hedge bot")
    parser.add_argument("--config", default="configs/core/drift_client.yaml", help="Path to configuration file")
    args = parser.parse_args()

    launcher = RealHedgeBetaLauncher(config_path=args.config, test_mode=args.test)
    await launcher.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[SHUTDOWN] Interrupted by user")
    except Exception as e:
        logger.error(f"[ERROR] Real beta hedge bot failed: {e}")
        sys.exit(1)

