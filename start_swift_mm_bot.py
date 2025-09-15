#!/usr/bin/env python3
"""
Startup script for the Complete Swift Market Making Bot
Handles environment setup and bot initialization
"""

import asyncio
import logging
import os
import sys
import subprocess
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def check_requirements():
    """Check if all requirements are met"""
    logger.info("🔍 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("Python 3.8+ required")
        return False
    
    # Check wallet file
    wallet_file = ".valid_wallet.json"
    if not os.path.exists(wallet_file):
        logger.error(f"Wallet file not found: {wallet_file}")
        logger.info("Please create a wallet file or run: python create_test_wallet.py")
        return False
    
    # Check if sidecar is running
    try:
        import requests
        response = requests.get("http://localhost:8787/health", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Swift sidecar is running")
        else:
            logger.warning("⚠️  Swift sidecar not responding properly")
    except Exception:
        logger.warning("⚠️  Swift sidecar not running - starting in mock mode")
    
    logger.info("✅ Requirements check complete")
    return True

def start_swift_sidecar():
    """Start the Swift sidecar service"""
    logger.info("🚀 Starting Swift sidecar...")
    
    try:
        # Check if Docker is available
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        
        # Start sidecar via Docker Compose
        subprocess.run([
            "docker-compose", "-f", "docker-compose.swift.yml", "up", "-d"
        ], check=True)
        
        # Wait for sidecar to be ready
        logger.info("⏳ Waiting for sidecar to be ready...")
        time.sleep(5)
        
        # Test sidecar health
        import requests
        for i in range(10):
            try:
                response = requests.get("http://localhost:8787/health", timeout=2)
                if response.status_code == 200:
                    logger.info("✅ Swift sidecar is ready")
                    return True
            except Exception:
                time.sleep(1)
        
        logger.warning("⚠️  Swift sidecar not ready, continuing anyway")
        return True
        
    except subprocess.CalledProcessError:
        logger.warning("⚠️  Docker not available, sidecar may not be running")
        return True
    except Exception as e:
        logger.warning(f"⚠️  Failed to start sidecar: {e}")
        return True

def setup_environment():
    """Setup environment variables"""
    logger.info("🔧 Setting up environment...")
    
    # Set default environment variables
    env_vars = {
        "DRIFT_ENV": "devnet",
        "RPC_URL": "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
        "SWIFT_SIDECAR_URL": "http://localhost:8787",
        "SWIFT_WEBSOCKET_URL": "wss://swift.drift.trade/ws",
        "LOG_LEVEL": "INFO"
    }
    
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
            logger.info(f"Set {key}={value}")
    
    logger.info("✅ Environment setup complete")

async def run_bot():
    """Run the complete Swift MM bot"""
    try:
        logger.info("🤖 Starting Complete Swift MM Bot...")
        
        # Import and run the bot
        from run_swift_mm_complete import main
        return await main()
        
    except Exception as e:
        logger.error(f"Failed to run bot: {e}")
        return 1

def main():
    """Main startup function"""
    try:
        logger.info("🚀 Swift Market Making Bot Startup")
        logger.info("=" * 50)
        
        # Check requirements
        if not check_requirements():
            logger.error("❌ Requirements not met")
            return 1
        
        # Setup environment
        setup_environment()
        
        # Start sidecar (optional)
        start_swift_sidecar()
        
        # Run the bot
        logger.info("🎯 Starting market making bot...")
        exit_code = asyncio.run(run_bot())
        
        logger.info(f"Bot finished with exit code: {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)



