#!/usr/bin/env python3
"""
Test Real DriftPy Trade V2 - Using instruction-based approach for older driftpy versions
"""
import asyncio
import json
import time
from libs.drift.drivers.driftpy import DriftPyDriver, DriftPyConfig
from libs.drift.client import Order, OrderSide

async def test_real_driftpy_trade_v2():
    """Test placing a real trade with DriftPy using instruction-based approach"""
    print("🚀 TESTING REAL DRIFTPY TRADE V2 (Instruction-based)")
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
        # Setup DriftPy
        print(f"\n🔧 Setting up DriftPy...")
        await driver.setup()
        
        if not driver.driftpy_ready:
            print(f"❌ DriftPy setup failed - cannot place real trade")
            return False
        
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
        print(f"   Type: LIMIT")
        
        # Place the order using instruction-based approach
        print(f"\n🚀 Placing REAL order on Drift devnet (V2)...")
        order_id = await driver._place_real_drift_order_v2(test_order)
        
        print(f"\n✅ Order Result:")
        print(f"   Order ID: {order_id}")
        
        if order_id.startswith("failed"):
            print(f"❌ Order failed: {order_id}")
            return False
        else:
            print(f"🎉 REAL ORDER PLACED SUCCESSFULLY!")
            print(f"🌐 Check beta.drift.trade for your order!")
            return True
            
    except Exception as e:
        print(f"❌ Error during real trade test: {e}")
        return False
    finally:
        await driver.close()

async def main():
    """Main function"""
    print("🔥 DRIFTPY REAL TRADE TEST V2")
    print("="*60)
    
    success = await test_real_driftpy_trade_v2()
    
    print(f"\n{'='*60}")
    print(f"📊 TEST RESULT: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"{'='*60}")
    
    if success:
        print(f"🎉 Real trade placed successfully!")
        print(f"💡 Check beta.drift.trade to see your order")
    else:
        print(f"❌ Real trade failed")
        print(f"💡 Check the error messages above")

if __name__ == "__main__":
    asyncio.run(main())
