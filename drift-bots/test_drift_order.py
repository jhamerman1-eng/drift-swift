#!/usr/bin/env python3
"""
Test Direct Drift Order - Places a real order on beta.drift.trade
"""
import asyncio
from libs.drift.client import build_client_from_config, Order, OrderSide

async def test_drift_order():
    print("🚀 TESTING DIRECT DRIFT ORDER PLACEMENT")
    print("="*60)
    print("This will place a REAL order on beta.drift.trade!")
    print("="*60)
    
    try:
        # Build client with DriftPy driver
        client = await build_client_from_config("configs/core/drift_client.yaml")
        
        print(f"✅ Client built: {type(client).__name__}")
        
        # Create a test order
        test_order = Order(
            side=OrderSide.BUY,
            price=149.50,  # Below current market
            size_usd=25.0  # Small order for testing
        )
        
        print(f"\n📝 Placing test order:")
        print(f"   Side: {test_order.side.value}")
        print(f"   Price: ${test_order.price}")
        print(f"   Size: ${test_order.size_usd}")
        
        # Place the order
        order_id = client.place_order(test_order)
        
        print(f"\n🎯 Order Result:")
        print(f"   Order ID: {order_id}")
        print(f"   Status: Submitted to Drift")
        
        # Get orderbook to show current market
        ob = client.get_orderbook()
        if ob.bids and ob.asks:
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
            print(f"\n📊 Current Market:")
            print(f"   Mid Price: ${mid:.2f}")
            print(f"   Top Bid: ${ob.bids[0][0]:.2f}")
            print(f"   Top Ask: ${ob.asks[0][0]:.2f}")
        
        print(f"\n🌐 Check beta.drift.trade for your order!")
        print(f"💡 Look for order ID: {order_id}")
        
        # Close client
        await client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_drift_order())
