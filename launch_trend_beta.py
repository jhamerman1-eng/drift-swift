#!/usr/bin/env python3
"""
🚀 Trend Bot - Beta.Drift.Trade Launcher
Launches the Trend Bot specifically in the beta.drift.trade environment.
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path
from typing import Dict, Any
from collections import deque

# Add libs directory to path
sys.path.append(str(Path(__file__).parent / "libs"))

# Configure logging
    handlers=[
        logging.FileHandler('trend_bot_beta.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import bot components
from libs.drift.client import build_client_from_config
from libs.order_management import PositionTracker, OrderManager
from orchestrator.risk_manager import RiskManager
from bots.trend.main import trend_iteration, load_trend_config
# Setup centralized logging
from libs.logging_config import setup_critical_logging
logger = setup_critical_logging("trend-bot")

class TrendBetaLauncher:
    """Launcher for Trend Bot in beta.drift.trade environment."""

    def __init__(self):
        self.client = None
        self.position_tracker = PositionTracker()
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager()
        self.iteration_count = 0
        self.errors = []
        self.running = True

        # Initialize data structures for trend analysis
        self.prices = deque(maxlen=1000)
        self.macd_values = deque(maxlen=1000)
        self.state_vars = {}  # For EMA state variables

    async def initialize_beta_client(self) -> bool:
        """Initialize Drift client for beta environment."""
        try:
            logger.info("Initializing Trend Bot for beta.drift.trade...")

            # Set devnet environment variables (using devnet for safety)
            os.environ["USE_MOCK"] = "false"
            os.environ["DRIFT_RPC_URL"] = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
            os.environ["DRIFT_WS_URL"] = "wss://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
            os.environ["DRIFT_KEYPAIR_PATH"] = ".valid_wallet.json"

            # Build client from config
            self.client = await build_client_from_config("configs/core/drift_client.yaml")

            logger.info("Trend Bot client initialized successfully!")
            logger.info("Strategy: MACD + Momentum with Anti-Chop Filters")
            logger.info("Target: SOL-PERP on Drift Protocol")
            logger.info("Environment: Devnet (Test Network)")
            logger.info("Orders will be visible on devnet.drift.trade")
            logger.warning("WARNING: TEST NETWORK - SAFE TO USE")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize Trend Bot client: {e}")
            return False

    async def load_trend_configuration(self) -> Dict[str, Any]:
        """Load trend bot configuration."""
        try:
            config = load_trend_config("configs/trend/filters.yaml")
            logger.info("Trend configuration loaded")
            return config
        except Exception as e:
            logger.error(f"Failed to load trend configuration: {e}")
            return {}

    async def run_trend_loop(self, config: Dict[str, Any]):
        """Main trend bot trading loop."""
        logger.info("Starting Trend Bot trading loop...")
        logger.info("Configuration: MACD(12,26,9) + Momentum(14) + Anti-Chop(50)")
        logger.info("Press Ctrl+C to stop gracefully")

        refresh_interval = config.get("refresh_interval", 1.0)

        while self.running:
            try:
                iteration_start = asyncio.get_event_loop().time()

                # Run one iteration of trend analysis
                await trend_iteration(
                    config, self.client, self.risk_manager,
                    self.position_tracker, self.order_manager,
                    self.prices, self.macd_values, self.state_vars
                )

                self.iteration_count += 1

                # Log progress every 10 iterations
                if self.iteration_count % 10 == 0:
                    logger.info(f"Completed {self.iteration_count} trend iterations")
                    logger.info(f"Current position: ${self.position_tracker.net_exposure:.2f}")
                    logger.info(f"Total volume: ${self.position_tracker.volume:.2f}")

                # Calculate sleep time to maintain refresh interval
                iteration_time = asyncio.get_event_loop().time() - iteration_start
                sleep_time = max(0, refresh_interval - iteration_time)

                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Error in trend iteration {self.iteration_count}: {e}")
                self.errors.append(str(e))

                # Continue running despite errors
                await asyncio.sleep(refresh_interval)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False

    async def show_startup_banner(self):
        """Display startup information."""
        print("=" * 80)
        logger.info("TREND BOT LAUNCHING IN DEVNET MODE")
        print("=" * 80)
        logger.info("Strategy: MACD + Momentum with Anti-Chop Filters")
        logger.info("Target: SOL-PERP on Drift Protocol")
        logger.info("Environment: Devnet (Test Network)")
        logger.info("Mode: TEST TRADING (safe to use!)")
        print("=" * 80)
        logger.info("Press Ctrl+C to stop gracefully")
        print()

    async def run(self) -> int:
        """Main launcher execution."""
        try:
            # Setup signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)

            # Show startup banner
            await self.show_startup_banner()

            # Initialize client
            if not await self.initialize_beta_client():
                logger.error("Failed to initialize client")
                return 1

            # Load configuration
            config = await self.load_trend_configuration()
            if not config:
                logger.error("Failed to load configuration")
                return 1

            # Start trading loop
            await self.run_trend_loop(config)

            # Show final statistics
            logger.info("=" * 60)
            logger.info("TREND BOT SHUTDOWN COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Total iterations: {self.iteration_count}")
            logger.info(f"Final position: ${self.position_tracker.net_exposure:.2f}")
            logger.info(f"Total volume: ${self.position_tracker.volume:.2f}")
            logger.info(f"Errors encountered: {len(self.errors)}")

            if self.errors:
                logger.warning("Last few errors:")
                for error in self.errors[-3:]:
                    logger.warning(f"   - {error}")

            logger.info("Trend Bot shutdown gracefully")
            return 0

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            self.running = False
            return 0

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            return 1

        finally:
            # Cleanup
            if self.client:
                try:
                    await self.client.close()
                    logger.info("Client connection closed")
                except Exception as e:
                    logger.error(f"Error closing client: {e}")

async def main():
    """Main entry point."""
    launcher = TrendBetaLauncher()
    return await launcher.run()

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nTrend Bot stopped by user")
        sys.exit(0)
