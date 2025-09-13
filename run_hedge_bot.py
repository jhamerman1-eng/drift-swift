#!/usr/bin/env python3
"""
Simple Hedge Bot Runner
Runs the hedge bot with proper configuration
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "bots"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_hedge_bot():
    """Run the hedge bot"""
    try:
        logger.info("🚀 Starting Hedge Bot")
        logger.info("=" * 50)
        
        # Import the hedge bot main function
        from bots.hedge.main import hedge_iteration
        
        # Load configuration
        import yaml
        with open("configs/core/drift_client.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        logger.info("📡 Configuration loaded")
        logger.info(f"🏦 Environment: {config.get('cluster', 'devnet')}")
        logger.info(f"🔗 RPC: {config.get('rpc_url', 'default')}")
        
        # Initialize components
        from libs.drift.client import build_client_from_config
        from libs.order_management import PositionTracker, OrderManager
        from orchestrator.risk_manager import RiskManager
        
        logger.info("🔧 Initializing components...")
        
        # Build client
        client = await build_client_from_config("configs/core/drift_client.yaml")
        logger.info("✅ Drift client initialized")
        
        # Initialize components
        position_tracker = PositionTracker()
        order_manager = OrderManager()
        risk_manager = RiskManager()
        
        logger.info("✅ All components initialized")
        
        # Load hedge configuration
        with open("configs/hedge/routing.yaml", "r") as f:
            hedge_config = yaml.safe_load(f)
        
        # Run hedge iteration
        logger.info("🔄 Running hedge iteration...")
        await hedge_iteration(
            cfg=hedge_config,
            client=client,
            risk_mgr=risk_manager,
            position=position_tracker,
            orders=order_manager
        )
        
        logger.info("✅ Hedge iteration completed")
        
    except Exception as e:
        logger.error(f"❌ Hedge bot failed: {e}")
        logger.exception("Full traceback:")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(run_hedge_bot())
        if success:
            logger.info("🎉 Hedge bot completed successfully!")
        else:
            logger.error("💥 Hedge bot failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("⏹️ Hedge bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)
