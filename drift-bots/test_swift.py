#!/usr/bin/env python3
"""
Test Swift Driver Integration
"""

import asyncio
from libs.drift.client import build_client_from_config

async def test_swift():
    print("🚀 Testing Swift Driver Integration...")
    
    try:
        # Build client with Swift driver
        client = await build_client_from_config("configs/core/drift_client.yaml")
        
        print(f"✅ Client built successfully: {type(client).__name__}")
        
        # Test orderbook
        ob = client.get_orderbook()
        print(f"✅ Orderbook: {len(ob.bids)} bids, {len(ob.asks)} asks")
        
        # Test order placement
        from libs.drift.client import Order, OrderSide
        
        test_order = Order(
            side=OrderSide.BUY,
            price=150.0,
            size_usd=10.0
        )
        
        print(f"📝 Testing order placement: {test_order.side.value} {test_order.size_usd} @ ${test_order.price}")
        
        order_id = client.place_order(test_order)
        print(f"✅ Order placed: {order_id}")
        
        # Close client
        await client.close()
        print("🔒 Client closed successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_swift())
