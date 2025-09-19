#!/usr/bin/env python3
"""
Quick Functional Test - Verify Core Bot Functionality
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def test_bot_initialization():
    """Test basic bot initialization and core functionality"""
    print("🧪 QUICK FUNCTIONAL TEST")
    print("=" * 50)

    try:
        # Import the bot
        print("📦 Importing bot...")
        from run_swift_mm_complete import CompleteSwiftMMBot
        print("✅ Bot import successful")

        # Test configuration
        config = {
            "env": "devnet",
            "rpc_url": "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
            "wallet_file": ".beta_dev_wallet.json",
            "order_size": 0.001,
            "max_orders_per_side": 1,
            "test_mode": True
        }

        print("🔧 Initializing bot...")
        bot = CompleteSwiftMMBot(config)

        # Test basic bot creation (skip full initialization for now)
        print("✅ Bot instance created successfully")

        # Test JIT components directly
        print("📊 Testing JIT components...")

        # Test volatility calculation
        volatility = bot.calculate_real_volatility()
        print(".4f")

        # Test inventory skew calculation
        skew = bot.inventory_manager.calculate_inventory_skew(bot.current_position)
        print(".4f")

        # Test spread calculation
        spread = bot.spread_manager.calculate_dynamic_spread(volatility, skew, 0.5)
        print(".2f")

        # Test orderbook creation
        from bots.jit.main import Orderbook
        ob = Orderbook(bids=[[200, 1]], asks=[[201, 1]], ts=time.time())
        print("✅ Orderbook created")

        # Test OBI calculation
        obi = bot.obi_calculator.calculate_obi(ob)
        print(".3f")

        # Get basic stats
        stats = bot.get_stats()
        print(f"📊 Stats retrieved: {len(stats)} metrics")

        print("✅ Core JIT functions working!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_jit_components():
    """Test JIT algorithm components"""
    print("\n🤖 TESTING JIT COMPONENTS")
    print("=" * 30)

    try:
        from bots.jit.main import JITConfig, InventoryManager, OBICalculator, SpreadManager, Orderbook

        # Test JIT config with required parameters
        config = JITConfig(
            symbol="SOL-PERP",
            leverage=10,
            post_only=True,
            obi_microprice=True,
            spread_bps_base=8.0,
            spread_bps_min=4.0,
            spread_bps_max=25.0,
            inventory_target=0.0,
            max_position_abs=120.0,
            cancel_replace_enabled=True,
            cancel_replace_interval_ms=1000,
            toxicity_guard=True
        )
        print("✅ JITConfig created")

        # Test inventory manager
        inv_manager = InventoryManager(config, "SOL-PERP")
        print("✅ InventoryManager created")

        # Test OBI calculator
        obi_calc = OBICalculator(levels=5)
        print("✅ OBICalculator created")

        # Test spread manager
        spread_mgr = SpreadManager(config)
        print("✅ SpreadManager created")

        # Test orderbook
        ob = Orderbook(bids=[[100, 1]], asks=[[101, 1]], ts=time.time())
        print("✅ Orderbook created")

        print("✅ All JIT components working!")
        return True

    except Exception as e:
        print(f"❌ JIT test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 STARTING FUNCTIONAL TESTS\n")

    results = {
        "bot_initialization": await test_bot_initialization(),
        "jit_components": await test_jit_components()
    }

    print("\n" + "=" * 50)
    print("📋 TEST RESULTS SUMMARY")
    print("=" * 50)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")

    total_tests = len(results)
    passed_tests = sum(results.values())

    print(f"\n📊 Overall: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - Bot is functional!")
        return 0
    else:
        print("⚠️  Some tests failed - check issues above")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
