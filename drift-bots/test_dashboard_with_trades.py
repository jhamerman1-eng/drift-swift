#!/usr/bin/env python3
"""
Test Dashboard with Real Trading Activity
"""
import asyncio
import time
from libs.drift.client import EnhancedMockDriftClient, Order, OrderSide

async def generate_trading_activity():
    """Generate realistic trading activity"""
    print("🚀 GENERATING TRADING ACTIVITY")
    print("="*60)
    
    # Create mock client
    client = EnhancedMockDriftClient("SOL-PERP", start=150.0, spread_bps=6.0)
    
    try:
        print("✅ Mock client created")
        
        # Generate some trading activity
        for cycle in range(5):
            print(f"\n📊 Trading Cycle {cycle + 1}:")
            
            # Get current market
            ob = client.get_orderbook()
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
            
            # Place some orders
            if cycle % 2 == 0:  # Even cycles: buy
                order = Order(side=OrderSide.BUY, price=mid + 0.05, size_usd=100)
                order_id = client.place_order(order)
                print(f"   BUY order: {order_id} @ ${order.price:.4f}")
            else:  # Odd cycles: sell
                order = Order(side=OrderSide.SELL, price=mid - 0.05, size_usd=100)
                order_id = client.place_order(order)
                print(f"   SELL order: {order_id} @ ${order.price:.4f}")
            
            # Wait for fills
            await asyncio.sleep(1)
            
            # Check current status
            pnl = client.get_pnl_summary()
            positions = client.get_positions()
            trades = client.get_trade_history()
            
            print(f"   Status: PnL ${pnl['total_pnl']:+.2f}, Positions: {len(positions)}, Trades: {len(trades)}")
        
        # Final status
        print(f"\n📊 FINAL TRADING STATUS:")
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
            for trade in trades[-5:]:
                print(f"     {trade.side.value.upper()} ${trade.size_usd:.2f} @ ${trade.price:.4f}")
        
        return client
        
    except Exception as e:
        print(f"❌ Error generating trading activity: {e}")
        import traceback
        traceback.print_exc()
        return None

def display_simple_dashboard(client):
    """Display a simple dashboard with the trading results"""
    print("\n" + "="*80)
    print("📊 SIMPLE PnL DASHBOARD - WITH REAL TRADING ACTIVITY")
    print("="*80)
    
    try:
        # Get current data
        pnl = client.get_pnl_summary()
        positions = client.get_positions()
        trades = client.get_trade_history()
        ob = client.get_orderbook()
        
        # Display portfolio summary
        print(f"💰 PORTFOLIO SUMMARY")
        print(f"   Total PnL:        ${pnl['total_pnl']:+.2f}")
        print(f"   Unrealized PnL:   ${pnl['unrealized_pnl']:+.2f}")
        print(f"   Realized PnL:     ${pnl['realized_pnl']:+.2f}")
        print(f"   Max Drawdown:     ${pnl['max_drawdown']:.2f}")
        print(f"   Peak Equity:      ${pnl['peak_equity']:.2f}")
        print(f"   Total Trades:     {len(trades)}")
        print(f"   Active Positions: {len(positions)}")
        
        # Display positions
        if positions:
            print(f"\n📈 CURRENT POSITIONS")
            for pos in positions:
                print(f"   {pos.size:+.4f} SOL @ ${pos.avg_price:.4f}")
                print(f"     Unrealized PnL: ${pos.unrealized_pnl:+.2f}")
                print(f"     Realized PnL:   ${pos.realized_pnl:+.2f}")
        else:
            print(f"\n📈 CURRENT POSITIONS: None")
        
        # Display recent trades
        if trades:
            print(f"\n📝 RECENT TRADES")
            for i, trade in enumerate(trades[-5:], 1):
                print(f"   {i}. {trade.side.value.upper()} ${trade.size_usd:.2f} @ ${trade.price:.4f}")
        else:
            print(f"\n📝 RECENT TRADES: None")
        
        # Display market info
        if ob.bids and ob.asks:
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
            spread = ob.asks[0][0] - ob.bids[0][0]
            spread_bps = (spread / mid) * 10000
            
            print(f"\n📊 MARKET STATE")
            print(f"   SOL-PERP: ${mid:.4f}")
            print(f"   Spread: {spread_bps:.2f} bps")
            print(f"   Top Bid: ${ob.bids[0][0]:.4f}")
            print(f"   Top Ask: ${ob.asks[0][0]:.4f}")
        
        print("\n" + "="*80)
        print("✅ Dashboard display complete!")
        
    except Exception as e:
        print(f"❌ Error displaying dashboard: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main function"""
    print("🔥 TESTING DASHBOARD WITH REAL TRADING ACTIVITY")
    print("="*60)
    
    # Generate trading activity
    client = await generate_trading_activity()
    
    if client:
        # Display dashboard
        display_simple_dashboard(client)
        
        # Clean up
        await client.close()
        print("🔒 Client closed")
    else:
        print("❌ Failed to generate trading activity")

if __name__ == "__main__":
    asyncio.run(main())
