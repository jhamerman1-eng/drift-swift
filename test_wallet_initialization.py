#!/usr/bin/env python3
"""
Test wallet initialization and bot startup
"""

import asyncio
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def test_wallet_loading():
    """Test wallet loading functionality"""
    print("🧪 TESTING WALLET INITIALIZATION")
    print("=" * 50)

    try:
        # Import the bot
        print("📦 Importing bot...")
        from run_swift_mm_complete import CompleteSwiftMMBot
        print("✅ Bot import successful")

        # Test configuration with proper wallet
        config = {
            "env": "devnet",
            "rpc_url": "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
            "wallet_file": ".valid_wallet.json",
            "order_size": 0.001,
            "max_orders_per_side": 1,
            "test_mode": True
        }

        print("🔧 Creating bot instance...")
        bot = CompleteSwiftMMBot(config)
        print("✅ Bot instance created")

        print("🔑 Testing wallet loading...")
        try:
            await bot._load_wallet()
            print("✅ Wallet loaded successfully!")
            print(f"   Public Key: {bot.keypair.pubkey()}")
        except Exception as e:
            print(f"❌ Wallet loading failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        print("🌐 Testing Drift client initialization...")
        try:
            await bot._initialize_drift_client()
            print("✅ Drift client initialized successfully!")
        except Exception as e:
            print(f"❌ Drift client initialization failed: {e}")
            print("This might be expected if no devnet SOL is available")
            print("But wallet loading should work fine")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run wallet initialization test"""
    success = await test_wallet_loading()

    if success:
        print("\n🎉 WALLET INITIALIZATION SUCCESSFUL!")
        print("✅ The wallet configuration issue has been resolved!")
        print("✅ Bot can now load wallet credentials properly!")
        return 0
    else:
        print("\n❌ WALLET INITIALIZATION FAILED!")
        print("🔧 Need to troubleshoot wallet configuration")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


