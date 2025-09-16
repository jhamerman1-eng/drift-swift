#!/usr/bin/env python3
"""
Simple Hedge Bot Runner
Runs the hedge bot with proper configuration using CENTRALIZED ENVIRONMENT CONFIG
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "bots"))

# CRITICAL: Import centralized environment configuration
from libs.config.environment import get_environment_config

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
        
        # CRITICAL: Load configuration from centralized environment config
        env_config = get_environment_config()
        
        # Validate configuration
        validation = env_config.validate_configuration()
        if not validation["valid"]:
            logger.error(f"❌ Environment configuration issues: {validation['issues']}")
            return
        
        logger.info("📡 Centralized configuration loaded")
        logger.info(f"🌍 Environment: {env_config.get_environment().upper()}")
        logger.info(f"🏦 Drift Environment: {env_config.get_drift_env()}")
        logger.info(f"🔗 RPC URL: {env_config.get_rpc_url()[:50]}...")
        logger.info(f"🚀 Swift URL: {env_config.get_swift_config()['base_url']}")
        logger.info(f"🎯 Use Local Sidecar: {env_config.use_local_sidecar()}")
        
        # Convert to legacy format for existing bot components
        legacy_config = {
            "cluster": env_config.get_drift_env(),
            "rpc_url": env_config.get_rpc_url(),
            "swift": env_config.get_swift_config(),
            "market_index": 0,  # SOL-PERP
            "use_mock": False,
            "live_trading": not env_config.is_local()
        }
        
        # Initialize components
        from libs.drift.client import build_client_from_config
        from libs.order_management import PositionTracker, OrderManager
        from orchestrator.risk_manager import RiskManager
        
        logger.info("🔧 Initializing components...")
        
        # Build client using converted config
        client = await build_client_from_legacy_config(legacy_config)
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
