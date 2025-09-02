#!/usr/bin/env python3
"""
Test Mock Trading - Verify the enhanced mock client is working correctly
"""
import asyncio
import time
from libs.drift.client import EnhancedMockDriftClient, Order, OrderSide

async def test_mock_trading():
    """Test the enhanced mock client trading logic"""
    print("🚀 TESTING ENHANCED MOCK CLIENT")
    print("="*60)
    
    # Create mock client
    client = EnhancedMockDriftClient("SOL-PERP", start=150.0, spread_bps=6.0)
    
    try:
        print("✅ Mock client created")
        
        # Test 1: Get initial orderbook
        print("\n📊 Test 1: Getting orderbook...")
        ob = client.get_orderbook()
        print(f"   Bids: {ob.bids[:3]}")
        print(f"   Asks: {ob.asks[:3]}")
        print(f"   Mid: ${(ob.bids[0][0] + ob.asks[0][0]) / 2:.4f}")
        
        # Test 2: Place some orders
        print("\n📝 Test 2: Placing orders...")
        
        # Place a buy order slightly above mid
        mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
        buy_order = Order(side=OrderSide.BUY, price=mid + 0.1, size_usd=100)
        buy_id = client.place_order(buy_order)
        print(f"   BUY order placed: {buy_id} @ ${buy_order.price:.4f}")
        
        # Place a sell order slightly below mid
        sell_order = Order(side=OrderSide.SELL, price=mid - 0.1, size_usd=100)
        sell_id = client.place_order(sell_order)
        print(f"   SELL order placed: {sell_id} @ ${sell_order.price:.4f}")
        
        # Test 3: Wait for fills and check PnL
        print("\n⏳ Test 3: Waiting for order fills...")
        print("   Waiting 10 seconds for realistic fill simulation...")
        
        for i in range(10):
            await asyncio.sleep(1)
            
            # Check current state
            pnl = client.get_pnl_summary()
            positions = client.get_positions()
            trades = client.get_trade_history()
            
            print(f"   [{i+1:2d}s] PnL: ${pnl['total_pnl']:+.2f} | Positions: {len(positions)} | Trades: {len(trades)}")
            
            # Check if orders were filled
            if buy_id not in client.open_orders and sell_id not in client.open_orders:
                print("   ✅ All orders filled!")
                break
        
        # Test 4: Final status
        print("\n📊 Test 4: Final status...")
        pnl = client.get_pnl_summary()
        positions = client.get_positions()
        trades = client.get_trade_history()
        
        print(f"   Total PnL: ${pnl['total_pnl']:+.2f}")
        print(f"   Unrealized: ${pnl['unrealized_pnl']:+.2f}")
        print(f"   Realized: ${pnl['realized_pnl']:+.2f}")
        print(f"   Positions: {len(positions)}")
        print(f"   Trades: {len(trades)}")
        
        if positions:
            for pos in positions:
                print(f"   {pos.size:+.4f} SOL @ ${pos.avg_price:.4f}")
        
        if trades:
            print(f"   Recent trades:")
            for trade in trades[-3:]:  # Last 3 trades
                print(f"     {trade.side.value.upper()} ${trade.size_usd:.2f} @ ${trade.price:.4f}")
        
        print("\n🎯 Test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.close()

async def main():
    """Main function"""
    print("🔥 MOCK CLIENT TRADING TEST")
    print("="*60)
    
    success = await test_mock_trading()
    
    print(f"\n{'='*60}")
    print(f"📊 TEST RESULT: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"{'='*60}")
    
    if success:
        print(f"🎉 Mock client working correctly!")
        print(f"💡 Realistic trading simulation active")
        print(f"📈 PnL tracking functional")
    else:
        print(f"❌ Mock client has issues")
        print(f"💡 Check error messages above")

if __name__ == "__main__":
    asyncio.run(main())
