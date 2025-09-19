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
            logger.error(f"ERROR: Environment configuration issues: {validation['issues']}")
            return False

        logger.info("Environment Configuration Validated")
        logger.info(f"  Environment: {self.env_config.get_environment().upper()}")
        logger.info(f"  Drift Environment: {self.env_config.get_drift_env()}")
        logger.info(f"  RPC URL: {self.env_config.get_rpc_url()[:50]}...")
        logger.info(f"  Swift URL: {self.env_config.get_swift_config()['base_url']}")
        logger.info(f"  Use Local Sidecar: {self.env_config.use_local_sidecar()}")
        logger.info(f"  JIT Enabled: {self.env_config.get_jit_config()['enabled']}")
        logger.info(f"  Is Production: {self.env_config.is_production()}")

        # Double-check we're in DEVNET mode for trading
        if self.env_config.get_environment() == "devnet":
            logger.info("SUCCESS: DEVNET MODE CONFIRMED - Ready for blockchain trading")
        elif self.env_config.get_environment() == "local":
            logger.warning("WARNING: LOCAL MODE DETECTED - This uses mock sidecar, not real blockchain!")
            logger.warning("HINT: To trade on DEVNET, use: python launch_bot_universal.py --bot mm --env devnet")

        if self.env_config.is_production():
            logger.warning("WARNING: RUNNING IN PRODUCTION MODE (REAL MONEY TRADING!)")
            response = input("Type 'CONFIRM' to proceed with production trading: ")
            if response != "CONFIRM":
                logger.error("Production mode not confirmed. Exiting.")
                return False

        return True
    
    async def launch_hedge_bot(self):
        """Launch hedge bot with centralized config"""
        logger.info("[H] Launching Hedge Bot")
        
        # Import hedge bot
        from run_hedge_bot import run_hedge_bot
        await run_hedge_bot()
    
    async def launch_trend_bot(self):
        """Launch trend bot with centralized config"""
        logger.info("[Tr] 📈 Launching Trend Bot")
        
        # Import trend bot - commented out due to missing module
        # from run_trend_bot_beta import run_trend_bot_centralized
        # await run_trend_bot_centralized()
        logger.warning("Trend bot not available - module run_trend_bot_beta not found")
    
    async def launch_market_making_bot(self):
        """Launch market making bot with centralized config"""
        logger.info("[MM] Launching Market Making Bot")

        # Import and create market making bot instance
        from run_swift_mm_complete import CompleteSwiftMMBot

        # Load configuration from our custom trading config
        import yaml
        config_path = "configs/live_trading_config.yaml"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            config = {}
        except UnicodeDecodeError:
            logger.warning(f"Encoding issue with {config_path}, trying alternative encoding")
            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                config = yaml.safe_load(f) or {}

        # Add environment-specific settings
        config.update({
            'env': self.env_config.get_drift_env(),
            'rpc_url': self.env_config.get_rpc_url(),
            'swift_config': self.env_config.get_swift_config(),
        })

        # Create bot with loaded config
        bot = CompleteSwiftMMBot(config)

        # Initialize the bot
        logger.info("Initializing Market Making Bot...")
        if not await bot.initialize():
            logger.error("ERROR: Failed to initialize bot")
            return

        logger.info("[MM] SUCCESS: Bot initialized successfully")
        logger.info(f"[MM] Order sizes configured: Buy={config.get('buy_order_size', 'default')} SOL, Sell={config.get('sell_order_size', 'default')} SOL")

        # Run the main market making loop
        await self.run_market_making_loop(bot)

    async def run_market_making_loop(self, bot):
        """Run the main market making loop"""
        import time
        import asyncio

        logger.info("Starting Market Making Loop")

        tick_interval = 0.1  # 100ms for high-frequency trading
        stats_interval = 5   # 5 seconds for stats
        last_stats = time.time()

        logger.info(f"⚡ Running at {tick_interval*1000:.0f}ms intervals")

        try:
            while True:
                try:
                    # Market making tick
                    await bot.market_making_tick()

                    # Print stats periodically
                    current_time = time.time()
                    if current_time - last_stats >= stats_interval:
                        logger.info("Market Making Stats:")
                        logger.info(f"  Orders placed: {getattr(bot, 'stats', {}).get('orders_placed', 0)}")
                        logger.info(f"  Active orders: {len(getattr(bot, 'active_orders', {}))}")
                        last_stats = current_time

                    # Wait for next tick
                    await asyncio.sleep(tick_interval)

                except Exception as e:
                    logger.error(f"ERROR: Error in market making tick: {e}")
                    await asyncio.sleep(tick_interval * 2)  # Wait longer on error

        except KeyboardInterrupt:
            logger.info("Market making loop stopped by user")
        except Exception as e:
            logger.error(f"ERROR: Fatal error in market making loop: {e}")
        finally:
            logger.info("Market making bot shutdown complete")

    async def launch_bot(self, bot_type: str):
        """Launch the specified bot"""
        if not await self.validate_environment():
            return
        
        logger.info("="*60)
        logger.info(f"LAUNCHING {bot_type.upper()} BOT")
        logger.info(f"Environment: {self.env_config.get_environment().upper()}")
        logger.info("="*60)
        
        if bot_type == "hedge":
            await self.launch_hedge_bot()
        elif bot_type == "trend":
            await self.launch_trend_bot()
        elif bot_type == "mm":
            await self.launch_market_making_bot()
        else:
            logger.error(f"ERROR: Unknown bot type: {bot_type}")
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
    
    # Set environment variable BEFORE creating any configs
    if args.env:
        import os
        os.environ["DRIFT_ENVIRONMENT"] = args.env
        logger.info(f"🔄 Environment set to: {args.env}")

    # Create launcher after environment is set
    launcher = UniversalBotLauncher()

    try:
        asyncio.run(launcher.launch_bot(args.bot))
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"ERROR: Bot failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main()



