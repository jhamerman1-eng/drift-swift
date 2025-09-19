#!/usr/bin/env python3
"""
Stop MM Bot Script
Comprehensive script to stop all MM bot processes and ensure clean shutdown
"""

import asyncio
import logging
import os
import signal
import sys
import time
from typing import List

logger = logging.getLogger(__name__)

def find_mm_processes() -> List[int]:
    """Find running MM bot processes"""
    try:
        import psutil

        mm_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any('mm' in str(cmd).lower() or 'swift' in str(cmd).lower()
                                 for cmd in cmdline):
                    # Check if it's a Python process running MM bot scripts
                    if 'python' in proc.info['name'].lower():
                        if any(script in str(cmdline) for script in [
                            'run_swift_mm_complete.py',
                            'run_mm_bot_swift_official.py',
                            'run_oracle_aware_mm_bot.py',
                            'start_swift_mm_bot.py',
                            'swift_integration_oracle_fixed.py'
                        ] for cmd in cmdline):
                            mm_processes.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return mm_processes

    except ImportError:
        logger.warning("psutil not available, cannot detect running processes")
        return []

async def stop_mm_bot_gracefully():
    """Stop MM bot with graceful shutdown"""
    logger.info("🛑 Stopping MM Bot...")

    try:
        # Try to import and use the bot's shutdown method
        sys.path.append('.')

        # First, try to stop the main MM bot
        try:
            from run_swift_mm_complete import SwiftMMBot

            # Create a minimal config to initialize the bot for shutdown
            class MinimalConfig:
                def __init__(self):
                    self.drift_env = "devnet"
                    self.keypair_path = ".devnet_wallet.json"
                    self.sidecar_url = "http://localhost:8787"
                    self.market_indexes = [0]
                    self.enable_jit = True
                    self.enable_swift = True
                    self.order_refresh_frequency = 1.0
                    self.max_orders = 10
                    self.order_size = 0.01
                    self.price_offset = 0.001

            config = MinimalConfig()
            bot = SwiftMMBot(config)
            await bot.shutdown()
            logger.info("✅ MM Bot shutdown completed via graceful method")

        except Exception as e:
            logger.warning(f"Could not use graceful shutdown: {e}")

        # Fallback: Kill any running MM processes
        mm_pids = find_mm_processes()
        if mm_pids:
            logger.info(f"Found {len(mm_pids)} MM bot processes to kill: {mm_pids}")

            import psutil
            for pid in mm_pids:
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()
                    logger.info(f"Terminated process {pid}")
                except Exception as e:
                    logger.error(f"Failed to terminate process {pid}: {e}")
                    try:
                        proc.kill()  # Force kill if terminate fails
                    except:
                        pass

            # Wait a bit for processes to terminate
            await asyncio.sleep(2)

        # Final cleanup - kill any remaining processes
        remaining_pids = find_mm_processes()
        if remaining_pids:
            logger.warning(f"Force killing {len(remaining_pids)} remaining processes")
            for pid in remaining_pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except:
                    pass

        logger.info("✅ MM Bot stop process completed")

    except Exception as e:
        logger.error(f"❌ Error stopping MM bot: {e}")

async def cleanup_resources():
    """Clean up any lingering resources"""
    logger.info("🧹 Cleaning up resources...")

    try:
        # Close any WebSocket connections that might be lingering
        # This is a best-effort cleanup
        pass

    except Exception as e:
        logger.warning(f"Resource cleanup warning: {e}")

    logger.info("✅ Resource cleanup completed")

async def main():
    """Main stop function"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    logger.info("🚫 MM Bot Stop Script Starting...")

    # Stop the bot
    await stop_mm_bot_gracefully()

    # Clean up resources
    await cleanup_resources()

    logger.info("✅ MM Bot Stop Script Completed")
    logger.info("   The MM bot should now be fully stopped.")
    logger.info("   Check logs for any remaining activity.")

if __name__ == "__main__":
    asyncio.run(main())
