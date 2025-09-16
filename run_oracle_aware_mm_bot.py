#!/usr/bin/env python3
"""
Oracle-Aware MM Bot
Runs the market maker bot with fixed Oracle order handling

This bot will process Oracle orders that were previously being filtered out
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Dict, Any

# Add paths
sys.path.append('.')

# Import our Oracle-aware components
from libs.config.environment import get_environment_config
from swift_integration_oracle_fixed import SwiftMMIntegrationV2_1, OracleAwareSwiftConfig

logger = logging.getLogger(__name__)

class OracleAwareMMBot:
    """Market Maker Bot with Oracle order support"""
    
    def __init__(self):
        self.config = get_environment_config("devnet")
        self.swift_integration = None
        self.running = False
        self.stats = {
            "start_time": time.time(),
            "total_orders": 0,
            "oracle_orders": 0,
            "market_orders": 0,
            "errors": 0
        }
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("🎯 Initializing Oracle-Aware MM Bot")
        logger.info("=" * 60)
        
        # Validate environment
        validation = self.config.validate_configuration()
        if not validation["valid"]:
            raise RuntimeError(f"Environment invalid: {validation['issues']}")
        
        logger.info(f"✅ Environment: {validation['config_summary']['drift_env']}")
        logger.info(f"✅ Swift: {validation['config_summary']['swift_url']}")
        
        # Load wallet
        import json
        from solders.keypair import Keypair
        
        with open('.devnet_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        keypair = Keypair.from_bytes(wallet_data)
        
        logger.info(f"✅ Wallet: {keypair.pubkey()}")
        
        # Initialize DriftClient
        from solana.rpc.async_api import AsyncClient
        from driftpy.drift_client import DriftClient
        
        connection = AsyncClient(self.config.get_rpc_url())
        drift_client = DriftClient(connection, keypair, env=self.config.get_drift_env())
        
        logger.info("📡 Subscribing to DriftClient...")
        await drift_client.subscribe()
        
        # Initialize UserMap
        from driftpy.user_map.user_map import UserMap
        from driftpy.user_map.user_map_config import UserMapConfig, WebsocketConfig
        
        ws_config = WebsocketConfig(resub_timeout_ms=30000, commitment="confirmed")
        user_map_config = UserMapConfig(
            drift_client=drift_client,
            subscription_config=ws_config,
            connection=connection,
            skip_initial_load=False,
            include_idle=False,
        )
        user_map = UserMap(user_map_config)
        
        logger.info("👥 Subscribing to UserMap...")
        await user_map.subscribe()
        
        # Initialize Oracle-Aware Swift Integration
        oracle_config = OracleAwareSwiftConfig(
            keypair=keypair,
            drift_client=drift_client,
            user_map=user_map,
            drift_env="devnet",
            market_indexes=[0, 1, 2],  # SOL, BTC, ETH
            enable_oracle_orders=True  # KEY: Enable Oracle orders!
        )
        
        self.swift_integration = SwiftMMIntegrationV2_1(oracle_config)
        await self.swift_integration.initialize()
        
        logger.info("✅ Oracle-Aware MM Bot initialized!")
        logger.info("🎯 Ready to process Oracle orders that were previously filtered")
        
    async def run(self):
        """Run the market maker bot"""
        logger.info("\n🚀 Starting Oracle-Aware MM Bot...")
        logger.info("🔍 Listening for ALL Swift orders (including Oracle orders)...")
        
        self.running = True
        
        try:
            # Start Swift order subscription
            swift_task = asyncio.create_task(
                self.swift_integration.start_swift_subscription()
            )
            
            # Start monitoring task
            monitor_task = asyncio.create_task(self._monitor_performance())
            
            # Wait for tasks
            await asyncio.gather(swift_task, monitor_task)
            
        except asyncio.CancelledError:
            logger.info("🛑 Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Bot error: {e}")
            self.stats["errors"] += 1
        finally:
            self.running = False
            await self._cleanup()
    
    async def _monitor_performance(self):
        """Monitor bot performance"""
        while self.running:
            await asyncio.sleep(30)  # Log every 30 seconds
            
            if not self.running:
                break
                
            # Get current stats
            swift_stats = self.swift_integration.get_stats()
            subscriber_stats = swift_stats.get("swift_subscriber_stats", {})
            runtime = time.time() - self.stats["start_time"]
            
            logger.info("📊 Oracle-Aware MM Bot Status:")
            logger.info(f"   ⏱️  Runtime: {runtime:.1f}s")
            logger.info(f"   📦 Total Orders Received: {subscriber_stats.get('orders_received', 0)}")
            logger.info(f"   🎯 Oracle Orders: {subscriber_stats.get('oracle_orders_received', 0)}")
            logger.info(f"   💰 Market Orders: {subscriber_stats.get('market_orders_received', 0)}")
            logger.info(f"   ✅ Orders Processed: {subscriber_stats.get('orders_processed', 0)}")
            logger.info(f"   ⏭️  Orders Filtered: {subscriber_stats.get('orders_filtered', 0)}")
            logger.info(f"   ❌ Errors: {subscriber_stats.get('errors', 0)}")
            
            # Show what's different from before
            oracle_count = subscriber_stats.get('oracle_orders_received', 0)
            if oracle_count > 0:
                logger.info(f"   🔥 SUCCESS: Processing {oracle_count} Oracle orders (previously filtered!)")
    
    async def _cleanup(self):
        """Clean up resources"""
        logger.info("🧹 Cleaning up...")
        
        if self.swift_integration:
            await self.swift_integration.stop()
        
        logger.info("✅ Cleanup completed")
    
    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False

async def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    
    # Create and run bot
    bot = OracleAwareMMBot()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, bot.handle_shutdown)
    signal.signal(signal.SIGTERM, bot.handle_shutdown)
    
    try:
        await bot.initialize()
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
