#!/usr/bin/env python3
"""
Simple MM Bot Demo - Core Market Making Logic
Demonstrates basic MM bot functionality without complex Swift integration
"""

import asyncio
import logging
import time
import sys
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleMMBot:
    """Simple Market Making Bot demonstrating core functionality"""

    def __init__(self):
        self.client = None
        self.running = False
        self.iteration_count = 0

    async def initialize(self):
        """Initialize the MM bot"""
        logger.info("🚀 Initializing Simple MM Bot")

        try:
            from libs.drift.client import DriftpyClient

            # Initialize client with devnet config
            self.client = DriftpyClient(
                cfg={"cluster": "devnet", "wallets": {"maker_keypair_path": ".valid_wallet.json"}},
                rpc_url="https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
            )

            logger.info("✅ MM Bot initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ MM Bot initialization failed: {e}")
            return False

    async def run_market_making_iteration(self):
        """Run a single market making iteration"""
        try:
            self.iteration_count += 1
            logger.info(f"📊 MM Iteration #{self.iteration_count}")

            # Get current market data
            try:
                orderbook = await self.client.get_orderbook(market_index=0)
                bids = len(orderbook.get('bids', []))
                asks = len(orderbook.get('asks', []))

                logger.info(f"📈 Market Data: {bids} bids, {asks} asks")

                # Simple market making logic
                if bids > 0 and asks > 0:
                    # Calculate spread and potential orders
                    best_bid = orderbook['bids'][0][0] if orderbook['bids'] else 0
                    best_ask = orderbook['asks'][0][0] if orderbook['asks'] else 0

                    if best_bid > 0 and best_ask > 0:
                        spread = best_ask - best_bid
                        mid_price = (best_bid + best_ask) / 2
                        spread_bps = (spread / mid_price) * 10000

                        logger.info(f"📊 Spread: ${spread:.4f} ({spread_bps:.2f} bps)")
                        logger.info(f"📈 Mid Price: ${mid_price:.4f}")
                        # In a real MM bot, this is where we would place limit orders
                        # For demo purposes, we just log the potential actions

                        # Calculate optimal quote prices
                        quote_bid = best_bid - (spread * 0.1)  # Quote 10% inside best bid
                        quote_ask = best_ask + (spread * 0.1)  # Quote 10% inside best ask

                        logger.info(f"💰 Quote Bid: ${quote_bid:.4f}")
                        logger.info(f"💰 Quote Ask: ${quote_ask:.4f}")
                        logger.info("💰 MM Strategy: Would place limit orders to capture spread")

            except Exception as e:
                logger.warning(f"Market data fetch failed: {e}")

            # Get monitoring stats
            if hasattr(self.client, 'get_monitoring_stats'):
                stats = self.client.get_monitoring_stats()
                logger.info(f"📊 Monitoring: {stats['variant_byte_warnings']} warnings, "
                           f"{stats['total_signatures']} signatures, "
                           f"{stats['verify_key_cache']['size']} cached keys")

        except Exception as e:
            logger.error(f"❌ MM iteration failed: {e}")

    async def run(self, max_iterations=10):
        """Run the MM bot for a specified number of iterations"""
        logger.info("🎯 Starting Simple MM Bot Demo")
        logger.info("=" * 60)

        if not await self.initialize():
            return

        self.running = True

        try:
            for i in range(max_iterations):
                if not self.running:
                    break

                await self.run_market_making_iteration()

                # Wait between iterations
                if i < max_iterations - 1:  # Don't wait after last iteration
                    logger.info("⏱️  Waiting 5 seconds before next iteration...")
                    await asyncio.sleep(5)

        except KeyboardInterrupt:
            logger.info("🛑 MM Bot interrupted by user")
        except Exception as e:
            logger.error(f"❌ MM Bot runtime error: {e}")
        finally:
            self.running = False
            logger.info("=" * 60)
            logger.info("🏁 Simple MM Bot Demo Complete")
            logger.info(f"Total iterations: {self.iteration_count}")
            logger.info("=" * 60)

async def main():
    """Main entry point"""
    bot = SimpleMMBot()
    await bot.run(max_iterations=5)  # Run for 5 iterations as demo

if __name__ == "__main__":
    asyncio.run(main())
