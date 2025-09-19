#!/usr/bin/env python3
"""
Test Fixed DriftPy Integration - Following Official Documentation
"""
import asyncio
import json
import os
from libs.drift.drivers.driftpy import DriftPyDriver, DriftPyConfig
from libs.drift.client import Order, OrderSide

async def test_fixed_driftpy():
    """Test the fixed DriftPy integration"""
    print("🚀 TESTING FIXED DRIFTPY INTEGRATION")
    print("="*60)
    print("📚 Following official Drift documentation:")
    print("   - Proper wallet initialization with anchorpy.Wallet")
    print("   - User account setup with add_user(0)")
    print("   - Client subscription with subscribe()")
    print("   - Correct parameter precision for SOL-PERP")
    print("="*60)

    # Configuration
    config = DriftPyConfig(
        rpc_url="https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
        wallet_secret_key=r"C:\Users\genuw\.config\solana\id_devnet_custom.json",
        env="devnet",
        market="SOL-PERP",
        market_index=0
    )

    print(f"📋 Configuration:")
    print(f"   RPC: {config.rpc_url}")
    print(f"   Wallet: {config.wallet_secret_key}")
    print(f"   Environment: {config.env}")
    print(f"   Market: {config.market}")

    # Create driver
    driver = DriftPyDriver(config)

    try:
        # Setup DriftPy following official docs
        print(f"\n🔧 Setting up DriftPy (following official docs)...")
        await driver.setup()

        if not driver.driftpy_ready:
            print(f"❌ DriftPy setup failed - cannot place real trade")
            return False

        print(f"✅ DriftPy setup successful!")
        print(f"✅ Wallet wrapped in anchorpy.Wallet")
        print(f"✅ User account setup complete")
        print(f"✅ Drift subscription active")

        # Create a test order
        test_order = Order(
            side=OrderSide.BUY,
            size_usd=25.0,  # $25 USD
            price=149.50    # $149.50 per SOL
        )

        print(f"\n📝 Test Order:")
        print(f"   Side: {test_order.side.value}")
        print(f"   Size: ${test_order.size_usd}")
        print(f"   Price: ${test_order.price}")
        print(f"   Expected SOL Amount: {test_order.size_usd / test_order.price:.6f} SOL")

        # Place the order
        print(f"\n🚀 Placing REAL order on Drift devnet...")
        order_id = await driver.place_order(test_order)

        print(f"\n✅ Order Result:")
        print(f"   Order ID: {order_id}")

        if order_id.startswith("failed"):
            print(f"❌ Order failed: {order_id}")
            return False
        elif order_id.startswith("sim_"):
            print(f"⚠️  Order simulated (fallback mode)")
            return False
        else:
            print(f"🎉 REAL ORDER PLACED SUCCESSFULLY!")
            print(f"🌐 Check beta.drift.trade for your order!")
            return True

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await driver.close()

async def main():
    """Main function"""
    print("🔥 DRIFTPY OFFICIAL DOCS COMPLIANCE TEST")
    print("="*60)

    success = await test_fixed_driftpy()

    print(f"\n{'='*60}")
    print(f"📊 TEST RESULT: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"{'='*60}")

    if success:
        print(f"🎉 Fixed DriftPy integration working!")
        print(f"💡 Following official documentation correctly")
        print(f"🌐 Real orders should appear on beta.drift.trade")
    else:
        print(f"❌ Integration still has issues")
        print(f"💡 Check error messages above")

if __name__ == "__main__":
    asyncio.run(main())
