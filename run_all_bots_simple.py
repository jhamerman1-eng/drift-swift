#!/usr/bin/env python3
"""
Simple Multi-Bot Launcher - Runs all 3 bots concurrently
"""

import subprocess
import sys
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

def run_bot(bot_name, command):
    """Run a bot as a subprocess"""
    try:
        logger.info(f"🚀 Starting {bot_name}...")
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"✅ {bot_name} started (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"❌ Failed to start {bot_name}: {e}")
        return None

def main():
    """Main function to run all bots"""
    logger.info("🎯 STARTING ALL 3 BOTS CONCURRENTLY")
    logger.info("=" * 50)

    # Bot configurations
    bots = [
        {
            "name": "JIT Market Maker",
            "command": "python run_mm_bot_v2.py --env beta --cfg configs/core/drift_client.yaml"
        },
        {
            "name": "Simple Hedge Bot",
            "command": "python simple_hedge_beta_launcher.py"
        },
        {
            "name": "Trend Bot",
            "command": "python launch_trend_beta.py"
        }
    ]

    # Start all bots
    processes = []
    for bot in bots:
        process = run_bot(bot["name"], bot["command"])
        if process:
            processes.append((bot["name"], process))
        time.sleep(1)  # Small delay between starts

    logger.info(f"✅ All {len(processes)} bots started successfully!")
    logger.info("=" * 50)

    try:
        # Monitor bots
        while True:
            active_processes = []
            for name, process in processes:
                if process.poll() is None:  # Still running
                    active_processes.append((name, process))
                else:
                    logger.warning(f"⚠️ {name} has stopped (exit code: {process.returncode})")

            processes = active_processes

            if not processes:
                logger.info("❌ All bots have stopped")
                break

            logger.info(f"🔄 Active bots: {len(processes)} - {[name for name, _ in processes]}")
            time.sleep(30)  # Check every 30 seconds

    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Monitoring error: {e}")

    # Cleanup
    logger.info("🧹 Shutting down all bots...")
    for name, process in processes:
        try:
            process.terminate()
            logger.info(f"✅ {name} terminated")
        except Exception as e:
            logger.warning(f"⚠️ Could not terminate {name}: {e}")

    logger.info("🔒 All bots shutdown complete")

if __name__ == "__main__":
    main()
