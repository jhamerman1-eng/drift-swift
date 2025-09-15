#!/usr/bin/env python3
"""
STABLE SWIFT TRADING TEST
Comprehensive test of bot stability with new configuration system
"""

import asyncio
import logging
import os
import sys
import time
import json
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("stable_swift_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def test_wallet_loading():
    """Test wallet loading with new configuration"""
    print("🔑 TESTING WALLET LOADING")
    print("-" * 30)

    try:
        from run_swift_mm_complete import CompleteSwiftMMBot
        from config_loader import load_swift_config

        # Load configuration
        config = load_swift_config()
        print("✅ Configuration loaded")

        # Create bot instance
        bot = CompleteSwiftMMBot(config)
        print("✅ Bot instance created")

        # Test wallet loading
        await bot._load_wallet()
        print(f"✅ Wallet loaded: {bot.keypair.pubkey()}")

        # Verify wallet matches expected
        expected_address = "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
        actual_address = str(bot.keypair.pubkey())

        if actual_address == expected_address:
            print("✅ Wallet address verified")
            return True
        else:
            print(f"❌ Address mismatch: Expected {expected_address}, got {actual_address}")
            return False

    except Exception as e:
        print(f"❌ Wallet loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_drift_client_initialization():
    """Test Drift client initialization"""
    print("\n🌐 TESTING DRIFT CLIENT INITIALIZATION")
    print("-" * 40)

    try:
        from run_swift_mm_complete import CompleteSwiftMMBot
        from config_loader import load_swift_config

        config = load_swift_config()
        bot = CompleteSwiftMMBot(config)

        # Load wallet first
        await bot._load_wallet()

        # Test Drift client initialization
        await bot._initialize_drift_client()
        print("✅ Drift client initialized")

        # Test basic connection
        slot = await bot.drift_client.connection.get_slot()
        print(f"✅ Connection verified: Slot {slot.value}")

        return True

    except Exception as e:
        print(f"❌ Drift client initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_full_bot_initialization():
    """Test complete bot initialization"""
    print("\n🤖 TESTING FULL BOT INITIALIZATION")
    print("-" * 35)

    try:
        from run_swift_mm_complete import CompleteSwiftMMBot
        from config_loader import load_swift_config

        config = load_swift_config()
        bot = CompleteSwiftMMBot(config)

        # Test full initialization
        if await bot.initialize():
            print("✅ Full bot initialization successful")

            # Test basic components
            stats = bot.get_stats()
            print(f"✅ Stats retrieved: {len(stats)} metrics")

            # Test JIT components
            vol = bot.calculate_real_volatility()
            print(".4f")

            skew = bot.inventory_manager.calculate_inventory_skew(0.0)
            print(".4f")

            # Test configuration values
            print("📋 Configuration verification:")
            print(f"  • Environment: {config.get('env')}")
            print(f"  • RPC URL: {config.get('rpc_url')}")
            print(f"  • Order Size: {config.get('order_size')}")
            print(f"  • Max Loss: ${config.get('max_daily_loss_usd')}")

            return True
        else:
            print("❌ Full bot initialization failed")
            return False

    except Exception as e:
        print(f"❌ Bot initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_configuration_stability():
    """Test configuration stability across multiple loads"""
    print("\n🔄 TESTING CONFIGURATION STABILITY")
    print("-" * 35)

    try:
        from config_loader import SwiftConfigLoader

        # Test multiple configuration loads
        results = []
        for i in range(3):
            loader = SwiftConfigLoader()
            config = loader.get_bot_config()
            results.append(config)

            if loader.validate_config():
                print(f"✅ Configuration load {i+1}: Valid")
            else:
                print(f"❌ Configuration load {i+1}: Invalid")
                return False

        # Verify consistency
        first_config = results[0]
        for i, config in enumerate(results[1:], 1):
            if config == first_config:
                print(f"✅ Configuration consistency {i+1}: Passed")
            else:
                print(f"❌ Configuration consistency {i+1}: Failed")
                return False

        print("✅ Configuration stability verified")
        return True

    except Exception as e:
        print(f"❌ Configuration stability test failed: {e}")
        return False

async def run_stability_test():
    """Run comprehensive stability test"""
    print("🚀 STABLE SWIFT TRADING STABILITY TEST")
    print("=" * 50)
    print("Testing wallet configuration, Drift client, and bot initialization")
    print("=" * 50)

    start_time = datetime.now()

    tests = [
        ("Wallet Loading", test_wallet_loading),
        ("Drift Client", test_drift_client_initialization),
        ("Full Bot Init", test_full_bot_initialization),
        ("Config Stability", test_configuration_stability)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🔬 Running: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"📊 {test_name}: {status}")
        except Exception as e:
            print(f"❌ {test_name}: EXCEPTION - {e}")
            results.append((test_name, False))

    # Summary
    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "=" * 50)
    print("📋 STABILITY TEST RESULTS SUMMARY")
    print("=" * 50)
    print(".2f")

    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)

    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")

    print(".1f")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Swift trading bot is STABLE and READY")
        print("\n🔧 Next steps:")
        print("1. Ensure Swift sidecar is running (localhost:8787)")
        print("2. Fund wallet with SOL for mainnet trading")
        print("3. Run: python run_swift_mm_complete.py")
        return True
    else:
        print(f"\n⚠️ {total_tests - passed_tests} tests failed")
        print("🔧 Check the errors above and fix issues")
        return False

async def main():
    """Main test execution"""
    try:
        success = await run_stability_test()

        # Save test results
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "version": "1.0.0",
            "description": "Stable Swift Trading Stability Test"
        }

        with open("stability_test_results.json", 'w') as f:
            json.dump(test_results, f, indent=2)

        print(f"\n📄 Results saved to: stability_test_results.json")

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
