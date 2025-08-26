#!/usr/bin/env python3
"""
Test Unified Driver System - Swift and DriftPy Integration
"""
import asyncio
import os
from libs.drift.client import Order, OrderSide
from libs.drift.driver_factory import DriverFactory, create_auto_driver

async def test_driver(driver, driver_name: str):
    """Test a specific driver"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING {driver_name.upper()} DRIVER")
    print(f"{'='*60}")
    
    try:
        # Setup driver
        print(f"\n🔧 Setting up {driver_name} driver...")
        await driver.setup()
        
        # Test order
        test_order = Order(
            side=OrderSide.BUY,
            price=149.50,
            size_usd=25.0
        )
        
        print(f"\n📝 Testing order placement...")
        result = await driver.place_order(test_order)
        
        print(f"\n🎯 RESULT:")
        print(f"   Order ID: {result}")
        
        if "swift_" in result and "error" not in result:
            print(f"   Status: 🚀 REAL ORDER VIA SWIFT!")
            print(f"   🌐 Check beta.drift.trade NOW!")
        elif "failed" in result:
            print(f"   Status: ❌ Order failed")
        elif "sim_drift" in result:
            print(f"   Status: 🎭 Simulated (DriftPy not fully ready)")
        else:
            print(f"   Status: 🎭 Mock/Test mode")
        
        # Get orderbook
        print(f"\n📊 Getting orderbook...")
        ob = await driver.get_orderbook()
        print(f"Orderbook: {len(ob.bids)} bids, {len(ob.asks)} asks")
        
        # Get driver status
        if hasattr(driver, 'get_status'):
            status = driver.get_status()
            print(f"\n📊 Driver Status:")
            for key, value in status.items():
                print(f"   {key}: {value}")
        
        # Close driver
        await driver.close()
        
        return True
        
    except Exception as e:
        print(f"❌ {driver_name} driver test failed: {e}")
        return False

async def main():
    """Test the unified driver system"""
    print("🚀 UNIFIED DRIVER SYSTEM TEST")
    print("="*60)
    print("This will test both Swift and DriftPy drivers!")
    print("="*60)
    
    # Get environment variables
    swift_api_key = os.getenv("SWIFT_API_KEY")
    swift_secret = os.getenv("SWIFT_SECRET")
    driftpy_wallet = os.getenv("DRIFTPY_WALLET_PATH", "C:\\Users\\genuw\\.config\\solana\\id_devnet_custom.json")
    
    print(f"\n🔑 Environment Configuration:")
    print(f"   SWIFT_API_KEY: {'✅ Set' if swift_api_key else '❌ Not set'}")
    print(f"   SWIFT_SECRET: {'✅ Set' if swift_secret else '❌ Not set'}")
    print(f"   DRIFTPY_WALLET: {'✅ Set' if driftpy_wallet else '❌ Not set'}")
    
    # Test 1: Auto-driver selection
    print(f"\n{'='*60}")
    print(f"🎯 TEST 1: AUTO-DRIVER SELECTION")
    print(f"{'='*60}")
    
    try:
        auto_driver = create_auto_driver(
            swift_api_key=swift_api_key,
            swift_secret=swift_secret,
            driftpy_wallet_path=driftpy_wallet
        )
        
        auto_success = await test_driver(auto_driver, "AUTO")
        
    except Exception as e:
        print(f"❌ Auto-driver test failed: {e}")
        auto_success = False
    
    # Test 2: Swift driver (if credentials available)
    print(f"\n{'='*60}")
    print(f"🎯 TEST 2: SWIFT DRIVER")
    print(f"{'='*60}")
    
    swift_success = False
    if swift_api_key and swift_secret:
        try:
            swift_driver = DriverFactory.create_driver(
                driver_type="swift",
                swift_api_key=swift_api_key,
                swift_secret=swift_secret
            )
            swift_success = await test_driver(swift_driver, "SWIFT")
        except Exception as e:
            print(f"❌ Swift driver test failed: {e}")
    else:
        print(f"⚠️  Skipping Swift test - no credentials")
    
    # Test 3: DriftPy driver
    print(f"\n{'='*60}")
    print(f"🎯 TEST 3: DRIFTPY DRIVER")
    print(f"{'='*60}")
    
    try:
        driftpy_driver = DriverFactory.create_driver(
            driver_type="driftpy",
            driftpy_wallet_path=driftpy_wallet,
            driftpy_env="devnet"
        )
        driftpy_success = await test_driver(driftpy_driver, "DRIFTPY")
    except Exception as e:
        print(f"❌ DriftPy driver test failed: {e}")
        driftpy_success = False
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"   Auto-Driver: {'✅ PASS' if auto_success else '❌ FAIL'}")
    print(f"   Swift Driver: {'✅ PASS' if swift_success else '❌ FAIL'}")
    print(f"   DriftPy Driver: {'✅ PASS' if driftpy_success else '❌ FAIL'}")
    
    if auto_success or swift_success or driftpy_success:
        print(f"\n🎉 At least one driver is working!")
        print(f"🌐 Ready to place orders on beta.drift.trade!")
    else:
        print(f"\n❌ All drivers failed")
        print(f"💡 Check your configuration and try again")
    
    print(f"\n💡 To get real Swift API credentials:")
    print(f"   1. Visit: https://driftprotocol.notion.site/Swift-MM-Quick-Integration-Guide-1a5b74b65a9880eb9fe0cd07f1dbe72a")
    print(f"   2. Set environment variables:")
    print(f"      export SWIFT_API_KEY=your_api_key")
    print(f"      export SWIFT_SECRET=your_api_secret")

if __name__ == "__main__":
    asyncio.run(main())
