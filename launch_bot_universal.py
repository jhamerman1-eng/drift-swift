#!/usr/bin/env python3
"""
Universal Bot Launcher - CENTRALIZED ENVIRONMENT CONFIG
Launches any bot (hedge, trend, market-making) using centralized environment configuration

Usage:
    # Local environment (mock sidecar)
    export DRIFT_ENVIRONMENT=local
    python launch_bot_universal.py --bot hedge
    python launch_bot_universal.py --bot trend  
    python launch_bot_universal.py --bot mm

    # Devnet environment (real Swift API)
    export DRIFT_ENVIRONMENT=devnet
    python launch_bot_universal.py --bot hedge

    # Production environment (REAL MONEY!)
    export DRIFT_ENVIRONMENT=mainnet
    python launch_bot_universal.py --bot mm
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))

# CRITICAL: Import centralized environment configuration
from libs.config.environment import get_environment_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UniversalBotLauncher:
    """Universal launcher for all bots using centralized configuration"""
    
    def __init__(self):
        self.env_config = get_environment_config()
        
    async def validate_environment(self):
        """Validate the environment configuration"""
        validation = self.env_config.validate_configuration()
        if not validation["valid"]:
            logger.error(f"❌ Environment configuration issues: {validation['issues']}")
            return False
        
        logger.info("🌍 Environment Configuration Validated")
        logger.info(f"  Environment: {self.env_config.get_environment().upper()}")
        logger.info(f"  Drift Environment: {self.env_config.get_drift_env()}")
        logger.info(f"  RPC URL: {self.env_config.get_rpc_url()[:50]}...")
        logger.info(f"  Swift URL: {self.env_config.get_swift_config()['base_url']}")
        logger.info(f"  Use Local Sidecar: {self.env_config.use_local_sidecar()}")
        logger.info(f"  JIT Enabled: {self.env_config.get_jit_config()['enabled']}")
        logger.info(f"  Is Production: {self.env_config.is_production()}")
        
        if self.env_config.is_production():
            logger.warning("⚠️  WARNING: RUNNING IN PRODUCTION MODE (REAL MONEY TRADING!)")
            response = input("Type 'CONFIRM' to proceed with production trading: ")
            if response != "CONFIRM":
                logger.error("Production mode not confirmed. Exiting.")
                return False
        
        return True
    
    async def launch_hedge_bot(self):
        """Launch hedge bot with centralized config"""
        logger.info("🚀 Launching Hedge Bot")
        
        # Import hedge bot
        from run_hedge_bot import run_hedge_bot
        await run_hedge_bot()
    
    async def launch_trend_bot(self):
        """Launch trend bot with centralized config"""
        logger.info("📈 Launching Trend Bot")
        
        # Import trend bot
        from run_trend_bot_beta import run_trend_bot_centralized
        await run_trend_bot_centralized()
    
    async def launch_market_making_bot(self):
        """Launch market making bot with centralized config"""
        logger.info("🎯 Launching Market Making Bot")
        
        # Import and create market making bot instance
        from run_swift_mm_complete import CompleteSwiftMMBot
        
        # Create bot with centralized config
        bot = CompleteSwiftMMBot()
        
        # Run the bot
        await bot.run()
    
    async def launch_bot(self, bot_type: str):
        """Launch the specified bot"""
        if not await self.validate_environment():
            return
        
        logger.info("="*60)
        logger.info(f"🤖 LAUNCHING {bot_type.upper()} BOT")
        logger.info(f"🌍 Environment: {self.env_config.get_environment().upper()}")
        logger.info("="*60)
        
        if bot_type == "hedge":
            await self.launch_hedge_bot()
        elif bot_type == "trend":
            await self.launch_trend_bot()
        elif bot_type == "mm":
            await self.launch_market_making_bot()
        else:
            logger.error(f"❌ Unknown bot type: {bot_type}")
            logger.error("Available bots: hedge, trend, mm")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Universal Bot Launcher with Centralized Environment Configuration")
    parser.add_argument(
        "--bot", 
        choices=["hedge", "trend", "mm"],
        required=True,
        help="Bot type to launch (hedge, trend, mm)"
    )
    parser.add_argument(
        "--env",
        choices=["local", "devnet", "mainnet"],
        help="Override environment (optional - uses DRIFT_ENVIRONMENT env var by default)"
    )
    
    args = parser.parse_args()
    
    # Override environment if specified
    if args.env:
        import os
        os.environ["DRIFT_ENVIRONMENT"] = args.env
        logger.info(f"🔄 Environment overridden to: {args.env}")
    
    # Create launcher
    launcher = UniversalBotLauncher()
    
    try:
        asyncio.run(launcher.launch_bot(args.bot))
    except KeyboardInterrupt:
        logger.info("👋 Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ Bot failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main()



