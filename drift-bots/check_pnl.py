#!/usr/bin/env python3
"""
Quick PnL Check Script
Shows current positions, PnL, and trading status
"""

import asyncio
from libs.drift.client import build_client_from_config

async def check_pnl():
    """Quick check of current PnL and positions."""
    
    print("💰 QUICK PnL CHECK")
    print("=" * 40)
    
    try:
        # Initialize client
        client = await build_client_from_config("configs/core/drift_client.yaml")
        
        # Get current state
        positions = client.get_positions()
        pnl_summary = client.get_pnl_summary()
        trades = client.get_trade_history()
        open_orders = client.open_orders
        
        # Market info
        ob = client.get_orderbook()
        mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
        
        print(f"📊 Market: ${mid:.4f}")
        print(f"📈 Total PnL: ${pnl_summary['total_pnl']:+.2f}")
        print(f"💼 Positions: {len([p for p in positions.values() if p.size != 0])}")
        print(f"📝 Trades: {len(trades)}")
        print(f"⏳ Open Orders: {len(open_orders)}")
        
        # Show positions if any
        if positions:
            print(f"\n💼 POSITIONS:")
            for market, pos in positions.items():
                if pos.size != 0:
                    print(f"  {market}: {pos.size:+.4f} SOL @ ${pos.avg_price:.4f}")
                    print(f"    Unrealized: ${pos.unrealized_pnl:+.2f}")
                    print(f"    Realized: ${pos.realized_pnl:+.2f}")
        
        # Show recent trades
        if trades:
            print(f"\n📝 RECENT TRADES:")
            for trade in trades[-3:]:  # Last 3 trades
                print(f"  {trade.side.upper()} ${trade.size_usd:.1f} @ ${trade.price:.4f}")
        
        await client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_pnl())
