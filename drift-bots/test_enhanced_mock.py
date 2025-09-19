#!/usr/bin/env python3
"""
Test script for the Enhanced Mock Drift Client
Demonstrates realistic trading simulation with position tracking and PnL calculation
"""

import asyncio
import time
from libs.drift.client import EnhancedMockDriftClient, Order, OrderSide

async def test_enhanced_mock():
    """Test the enhanced mock client's trading simulation capabilities."""
    
    print("🚀 Testing Enhanced Mock Drift Client")
    print("=" * 50)
    
    # Initialize client
    client = EnhancedMockDriftClient(market="SOL-PERP", start=150.0)
    
    # Show initial state
    print(f"📊 Initial Market State:")
    ob = client.get_orderbook()
    mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
    print(f"   Mid: ${mid:.4f}")
    print(f"   Top Bid: ${ob.bids[0][0]:.4f} (${ob.bids[0][1]:.1f})")
    print(f"   Top Ask: ${ob.asks[0][0]:.4f} (${ob.asks[0][1]:.1f})")
    print()
    
    # Place some orders
    print("📝 Placing Orders:")
    
    # Buy order above mid (likely to fill)
    buy_order = Order(side=OrderSide.BUY, price=mid + 0.5, size_usd=100.0)
    buy_id = client.place_order(buy_order)
    print(f"   BUY: ${buy_order.size_usd:.1f} USD @ ${buy_order.price:.4f} → {buy_id}")
    
    # Sell order below mid (likely to fill)
    sell_order = Order(side=OrderSide.SELL, price=mid - 0.5, size_usd=50.0)
    sell_id = client.place_order(sell_order)
    print(f"   SELL: ${sell_order.size_usd:.1f} USD @ ${sell_order.price:.4f} → {sell_id}")
    
    # Aggressive buy order (very likely to fill)
    aggressive_buy = Order(side=OrderSide.BUY, price=mid + 2.0, size_usd=200.0)
    agg_buy_id = client.place_order(aggressive_buy)
    print(f"   AGGRESSIVE BUY: ${aggressive_buy.size_usd:.1f} USD @ ${aggressive_buy.price:.4f} → {agg_buy_id}")
    
    print()
    
    # Wait for orders to potentially fill
    print("⏳ Waiting for order fills...")
    for i in range(10):
        time.sleep(1)
        
        # Show current state
        ob = client.get_orderbook()
        mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
        
        positions = client.get_positions()
        pnl_summary = client.get_pnl_summary()
        trades = client.get_trade_history()
        
        print(f"   [{i+1:2d}s] Mid: ${mid:.4f} | PnL: ${pnl_summary['total_pnl']:.2f} | Trades: {len(trades)} | Open Orders: {len(client.open_orders)}")
        
        # Show positions if any
        if positions:
            for market, pos in positions.items():
                if pos.size != 0:
                    print(f"      {market}: {pos.size:+.4f} SOL @ ${pos.avg_price:.4f} | Unrealized: ${pos.unrealized_pnl:.2f}")
    
    print()
    
    # Final summary
    print("📈 Final Summary:")
    print("=" * 50)
    
    # Market state
    ob = client.get_orderbook()
    mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
    print(f"Final Mid: ${mid:.4f}")
    
    # PnL summary
    pnl_summary = client.get_pnl_summary()
    print(f"Total PnL: ${pnl_summary['total_pnl']:.2f}")
    print(f"Unrealized PnL: ${pnl_summary['unrealized_pnl']:.2f}")
    print(f"Realized PnL: ${pnl_summary['realized_pnl']:.2f}")
    print(f"Max Drawdown: ${pnl_summary['max_drawdown']:.2f}")
    print(f"Peak Equity: ${pnl_summary['peak_equity']:.2f}")
    
    # Positions
    positions = client.get_positions()
    if positions:
        print(f"\nPositions:")
        for market, pos in positions.items():
            if pos.size != 0:
                print(f"  {market}: {pos.size:+.4f} SOL @ ${pos.avg_price:.4f}")
                print(f"    Unrealized PnL: ${pos.unrealized_pnl:.2f}")
                print(f"    Realized PnL: ${pos.realized_pnl:.2f}")
    
    # Trade history
    trades = client.get_trade_history()
    if trades:
        print(f"\nTrade History ({len(trades)} trades):")
        for trade in trades[-5:]:  # Show last 5 trades
            timestamp = time.strftime("%H:%M:%S", time.localtime(trade.timestamp))
            print(f"  {timestamp} | {trade.side.upper()} {trade.size_usd:.1f} USD @ ${trade.price:.4f} → {trade.fill_id}")
    
    # Open orders
    if client.open_orders:
        print(f"\nOpen Orders ({len(client.open_orders)}):")
        for order_id, order in client.open_orders.items():
            print(f"  {order_id}: {order.side.upper()} {order.size_usd:.1f} USD @ ${order.price:.4f}")
    
    print()
    print("✅ Enhanced Mock Client Test Complete!")
    
    # Close client
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_enhanced_mock())
