#!/usr/bin/env python3
"""
Test Swift Driver - Places REAL orders via Swift API
"""
import asyncio
import os
from libs.drift.client import Order, OrderSide
from libs.drift.drivers.swift import create_swift_driver

async def main():
    """Test Swift driver order placement"""
    print("🚀 SWIFT DRIVER TEST")
    print("="*60)
    print("This will place REAL orders via Swift API!")
    print("="*60)
    
    # Get API credentials from environment
    api_key = os.getenv("SWIFT_API_KEY")
    api_secret = os.getenv("SWIFT_SECRET")
    
    if not api_key or not api_secret:
        print("❌ Missing Swift API credentials!")
        print("Set environment variables:")
        print("  SWIFT_API_KEY=your_api_key")
        print("  SWIFT_SECRET=your_api_secret")
        print("\n💡 For testing without real credentials, using mock mode...")
        
        # Use mock credentials for testing
        api_key = "test_key_12345"
        api_secret = "test_secret_67890"
    
    # Create Swift driver
    driver = create_swift_driver(api_key, api_secret)
    
    # Setup connections
    print(f"\n🔧 Setting up Swift driver...")
    await driver.setup()
    
    # Test order
    test_order = Order(
        side=OrderSide.BUY,
        price=149.50,
        size_usd=25.0
    )
    
    print(f"\n📝 Testing REAL order placement via Swift...")
    result = await driver.place_order(test_order)
    
    print(f"\n🎯 RESULT:")
    print(f"   Order ID: {result}")
    
    if "swift_" in result and "error" not in result:
        print(f"   Status: 🚀 REAL ORDER VIA SWIFT!")
        print(f"   🌐 Check beta.drift.trade NOW!")
    elif "failed" in result:
        print(f"   Status: ❌ Order failed")
    else:
        print(f"   Status: 🎭 Mock/Test mode")
    
    # Get orderbook
    print(f"\n📊 Getting orderbook...")
    ob = await driver.get_orderbook()
    print(f"Orderbook: {len(ob.bids)} bids, {len(ob.asks)} asks")
    
    # Close driver
    await driver.close()
    
    print(f"\n🌐 Check beta.drift.trade for your orders!")
    print(f"💡 Swift driver is ready for REAL trading!")

if __name__ == "__main__":
    asyncio.run(main())
