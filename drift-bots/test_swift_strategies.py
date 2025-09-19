#!/usr/bin/env python3
"""
Test Swift Order Strategies - Different order types and sizes
"""

import asyncio
import time
from libs.drift.client import build_client_from_config, Order, OrderSide

async def test_swift_strategies():
    print("🚀 Testing Swift Order Strategies...")
    print("=" * 60)
    
    try:
        # Build client with Swift driver
        client = await build_client_from_config("configs/core/drift_client.yaml")
        
        print(f"✅ Client built successfully: {type(client).__name__}")
        print(f"🌐 Swift API: {client.swift_base}")
        print(f"📊 Market: {client.market}")
        print()
        
        # Test 1: Market Making Orders
        print("📊 STRATEGY 1: Market Making (Tight Spread)")
        print("-" * 40)
        
        mid_price = 150.0
        spread = 0.1  # Tight 10 cent spread
        
        bid_order = Order(
            side=OrderSide.BUY,
            price=mid_price - spread/2,
            size_usd=25.0
        )
        
        ask_order = Order(
            side=OrderSide.SELL,
            price=mid_price + spread/2,
            size_usd=25.0
        )
        
        print(f"📝 Placing BUY: ${bid_order.size_usd:.1f} @ ${bid_order.price:.4f}")
        bid_id = client.place_order(bid_order)
        print(f"✅ Bid placed: {bid_id}")
        
        print(f"📝 Placing SELL: ${ask_order.size_usd:.1f} @ ${ask_order.price:.4f}")
        ask_id = client.place_order(ask_order)
        print(f"✅ Ask placed: {ask_id}")
        
        print()
        
        # Test 2: Aggressive Orders
        print("📊 STRATEGY 2: Aggressive Orders (Market Impact)")
        print("-" * 40)
        
        aggressive_buy = Order(
            side=OrderSide.BUY,
            price=mid_price + 0.05,  # Slightly above mid
            size_usd=100.0  # Larger size
        )
        
        print(f"📝 Placing aggressive BUY: ${aggressive_buy.size_usd:.1f} @ ${aggressive_buy.price:.4f}")
        agg_id = client.place_order(aggressive_buy)
        print(f"✅ Aggressive order placed: {agg_id}")
        
        print()
        
        # Test 3: Small Orders (High Frequency)
        print("📊 STRATEGY 3: High Frequency (Small Orders)")
        print("-" * 40)
        
        for i in range(3):
            small_order = Order(
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                price=mid_price + (i * 0.01) - 0.02,
                size_usd=5.0
            )
            
            print(f"📝 Placing small order {i+1}: {small_order.side.value} ${small_order.size_usd:.1f} @ ${small_order.price:.4f}")
            small_id = client.place_order(small_order)
            print(f"✅ Small order placed: {small_id}")
            
            time.sleep(0.5)  # Small delay between orders
        
        print()
        
        # Test 4: Cancel All Orders
        print("📊 STRATEGY 4: Cancel All Orders")
        print("-" * 40)
        
        print("🔄 Cancelling all open orders...")
        client.cancel_all()
        print("✅ All orders cancelled")
        
        print()
        
        # Show final status
        print("📊 FINAL STATUS")
        print("-" * 40)
        
        ob = client.get_orderbook()
        if ob.bids and ob.asks:
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
            print(f"🎯 Current mid price: ${mid:.4f}")
        
        trades = client.get_trade_history()
        print(f"📝 Total trades executed: {len(trades)}")
        
        # Close client
        await client.close()
        print("🔒 Client closed successfully")
        
        print("\n🎉 Swift Strategy Testing Complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_swift_strategies())
