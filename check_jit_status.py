#!/usr/bin/env python3
"""
Check JIT MM Bot Status and Dependencies
"""

import asyncio
import requests
import socket
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

def check_sidecar_status():
    """Check if Swift sidecar is running"""
    try:
        response = requests.get("http://localhost:8787/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return True, data.get('status', 'unknown')
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"

def check_wallet_file():
    """Check if wallet file exists"""
    wallet_path = Path(".devnet_wallet.json")
    if wallet_path.exists():
        return True, f"Wallet file found ({wallet_path.stat().st_size} bytes)"
    else:
        return False, "Wallet file not found"

def check_config_files():
    """Check if required config files exist"""
    required_configs = [
        "configs/jitter/shotgun.yaml",
        "configs/jitter/sniper.yaml",
        "configs/jitter/feature_flags.yaml"
    ]

    missing = []
    for config in required_configs:
        if not Path(config).exists():
            missing.append(config)

    if missing:
        return False, f"Missing config files: {missing}"
    else:
        return True, "All config files present"

def check_running_processes():
    """Check for running JIT processes"""
    try:
        import psutil
        jit_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any('jit' in str(cmd).lower() or 'mm' in str(cmd).lower()
                                 for cmd in cmdline):
                    jit_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': ' '.join(cmdline) if cmdline else 'N/A'
                    })
            except:
                continue

        return True, jit_processes
    except ImportError:
        return False, "psutil not available for process checking"

async def check_jit_status():
    """Comprehensive JIT status check"""
    logger.info("🔍 JIT MM Bot Status Check")
    logger.info("=" * 50)

    # Check sidecar
    logger.info("📡 Checking Swift Sidecar...")
    sidecar_ok, sidecar_status = check_sidecar_status()
    if sidecar_ok:
        logger.info(f"   ✅ Sidecar running: {sidecar_status}")
    else:
        logger.error(f"   ❌ Sidecar not running: {sidecar_status}")
        logger.error("   💡 Start sidecar with: npm run start (in swift-sidecar directory)")

    # Check wallet
    logger.info("🔑 Checking Wallet...")
    wallet_ok, wallet_status = check_wallet_file()
    if wallet_ok:
        logger.info(f"   ✅ {wallet_status}")
    else:
        logger.error(f"   ❌ {wallet_status}")

    # Check configs
    logger.info("⚙️ Checking Configuration...")
    config_ok, config_status = check_config_files()
    if config_ok:
        logger.info(f"   ✅ {config_status}")
    else:
        logger.error(f"   ❌ {config_status}")

    # Check processes
    logger.info("🔍 Checking Running Processes...")
    proc_ok, processes = check_running_processes()
    if proc_ok and processes:
        logger.info(f"   📊 Found {len(processes)} JIT-related processes:")
        for proc in processes:
            logger.info(f"      PID {proc['pid']}: {proc['name']} - {proc['cmdline'][:80]}...")
    elif proc_ok:
        logger.info("   📊 No JIT processes currently running")
    else:
        logger.warning(f"   ⚠️ {processes}")

    # Overall status
    logger.info("📋 Overall Status:")
    all_good = sidecar_ok and wallet_ok and config_ok
    if all_good:
        logger.info("   ✅ All systems ready for JIT MM bot")
        logger.info("   🎯 To start in shotgun mode: python start_jit_mm_shotgun.py")
    else:
        logger.error("   ❌ Some dependencies missing - JIT bot may not work properly")
        logger.info("   🔧 Fix the issues above before starting the bot")

    return all_good

async def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    await check_jit_status()

if __name__ == "__main__":
    asyncio.run(main())
