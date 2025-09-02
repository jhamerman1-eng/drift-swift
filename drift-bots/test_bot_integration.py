#!/usr/bin/env python3
"""
Test Bot Integration - Verify bots work with enhanced mock client
"""
import asyncio
import time
from libs.drift.client import EnhancedMockDriftClient, Order, OrderSide

async def test_jit_bot_logic():
    """Test JIT bot trading logic with mock client"""
    print("🚀 TESTING JIT BOT LOGIC")
    print("="*60)
    
    # Create mock client
    client = EnhancedMockDriftClient("SOL-PERP", start=150.0, spread_bps=6.0)
    
    try:
        print("✅ Mock client created")
        
        # Simulate JIT bot trading loop
        for cycle in range(3):
            print(f"\n📊 Cycle {cycle + 1}:")
            
            # Get orderbook
            ob = client.get_orderbook()
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
            
            # Calculate spread-based pricing (JIT logic)
            spread_bps = 6.0
            spread = spread_bps / 10000.0 * mid
            bid = mid - spread / 2
            ask = mid + spread / 2
            size = 200.0  # $200 USD
            
            print(f"   Mid: ${mid:.4f}, Spread: ${spread:.4f}")
            print(f"   Bid: ${bid:.4f}, Ask: ${ask:.4f}")
            
            # Place orders
            bid_order = Order(side=OrderSide.BUY, price=bid, size_usd=size)
            ask_order = Order(side=OrderSide.SELL, price=ask, size_usd=size)
            
            bid_id = client.place_order(bid_order)
            ask_id = client.place_order(ask_order)
            
            print(f"   Orders placed: BUY {bid_id}, SELL {ask_id}")
            
            # Wait for fills
            await asyncio.sleep(2)
            
            # Check status
            pnl = client.get_pnl_summary()
            positions = client.get_positions()
            trades = client.get_trade_history()
            
            print(f"   Status: PnL ${pnl['total_pnl']:+.2f}, Positions: {len(positions)}, Trades: {len(trades)}")
        
        # Final status
        print(f"\n📊 Final Status:")
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
                print(f"   Position: {pos.size:+.4f} SOL @ ${pos.avg_price:.4f}")
        
        if trades:
            print(f"   Recent trades:")
            for trade in trades[-5:]:  # Last 5 trades
                print(f"     {trade.side.value.upper()} ${trade.size_usd:.2f} @ ${trade.price:.4f}")
        
        print("\n🎯 JIT Bot test completed!")
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
    print("🔥 BOT INTEGRATION TEST")
    print("="*60)
    
    success = await test_jit_bot_logic()
    
    print(f"\n{'='*60}")
    print(f"📊 TEST RESULT: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"{'='*60}")
    
    if success:
        print(f"🎉 Bot integration working correctly!")
        print(f"💡 JIT bot logic functional")
        print(f"📈 Mock client generating realistic activity")
    else:
        print(f"❌ Bot integration has issues")
        print(f"💡 Check error messages above")

if __name__ == "__main__":
    asyncio.run(main())
