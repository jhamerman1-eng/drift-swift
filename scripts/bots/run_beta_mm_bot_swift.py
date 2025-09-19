#!/usr/bin/env python3
"""
Beta MM Bot with Swift Integration
Runs the market maker bot in beta devnet mode using validated Swift integration

This follows the complete Swift MM Quick Integration Guide:
- Real SwiftOrderSubscriber with WebSocket connection
- DriftClient and UserMap subscriptions  
- Place-and-make transaction building
- No fallbacks, no mock data - real on-chain orders only
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Dict, Any, Optional

# Add paths
sys.path.append('.')

# Import our validated components
from libs.config.environment import get_environment_config
from swift_integration_v2 import SwiftMMIntegrationV2, SwiftIntegrationConfig

logger = logging.getLogger(__name__)

class BetaMMBot:
    """Beta Market Maker Bot with real Swift integration"""
    
    def __init__(self):
        self.config = get_environment_config("devnet")
        self.swift_integration = None
        self.running = False
        self.stats = {
            "start_time": time.time(),
            "orders_placed": 0,
            "swift_orders_received": 0,
            "errors": 0
        }
        
    async def initialize(self):
        """Initialize all components for beta trading"""
        logger.info("🚀 Initializing Beta MM Bot for Devnet Trading")
        logger.info("=" * 60)
        
        # Validate environment
        validation = self.config.validate_configuration()
        if not validation["valid"]:
            raise RuntimeError(f"Environment invalid: {validation['issues']}")
        
        logger.info(f"✅ Environment: {validation['config_summary']['drift_env']}")
        logger.info(f"✅ RPC: {validation['config_summary']['rpc_url']}")
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
        
        # Initialize Swift Integration
        integration_config = SwiftIntegrationConfig(
            keypair=keypair,
            drift_client=drift_client,
            user_map=user_map,
            drift_env="devnet",
            market_indexes=[0, 1, 2],  # SOL, BTC, ETH
            enable_jit=True
        )
        
        self.swift_integration = SwiftMMIntegrationV2(integration_config)
        await self.swift_integration.initialize()
        
        logger.info("✅ Beta MM Bot initialized successfully!")
        logger.info("🎯 Ready to trade on devnet with real Swift orders")
        
    async def run(self):
        """Run the market maker bot"""
        logger.info("\n🔄 Starting Beta MM Bot...")
        logger.info("🔍 Listening for Swift orders...")
        
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
        """Monitor bot performance and log statistics"""
        while self.running:
            await asyncio.sleep(30)  # Log every 30 seconds
            
            if not self.running:
                break
                
            # Get current stats
            swift_stats = self.swift_integration.get_stats()
            runtime = time.time() - self.stats["start_time"]
            
            logger.info("📊 Beta MM Bot Status:")
            logger.info(f"   ⏱️  Runtime: {runtime:.1f}s")
            logger.info(f"   📦 Swift Orders Received: {swift_stats['swift_orders_received']}")
            logger.info(f"   ✅ Swift Orders Processed: {swift_stats['swift_orders_processed']}")
            logger.info(f"   🎯 JIT Orders Placed: {swift_stats['jit_orders_placed']}")
            logger.info(f"   ❌ Errors: {swift_stats['errors']}")
    
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
    bot = BetaMMBot()
    
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



