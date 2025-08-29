#!/usr/bin/env python3
"""
Quick PnL Check - Shows current PnL for all three bots
"""

from libs.drift.client import EnhancedMockDriftClient

def main():
    print("🚀 Quick PnL Check for All Three Bots")
    print("=" * 50)
    
    # Create clients for each bot
    jit_client = EnhancedMockDriftClient("SOL-PERP", start=150.0)
    trend_client = EnhancedMockDriftClient("SOL-PERP", start=150.0)
    hedge_client = EnhancedMockDriftClient("SOL-PERP", start=150.0)
    
    # Get PnL for each bot
    jit_pnl = jit_client.get_pnl_summary()['total_pnl']
    trend_pnl = trend_client.get_pnl_summary()['total_pnl']
    hedge_pnl = hedge_client.get_pnl_summary()['total_pnl']
    
    # Calculate total
    total_pnl = jit_pnl + trend_pnl + hedge_pnl
    
    print(f"\n💰 PORTFOLIO SUMMARY:")
    print(f"📊 Total PnL:        ${total_pnl:+.2f}")
    print(f"📈 JIT Bot:          ${jit_pnl:+.2f}")
    print(f"📈 Trend Bot:        ${trend_pnl:+.2f}")
    print(f"📈 Hedge Bot:        ${hedge_pnl:+.2f}")
    
    print(f"\n🤖 DETAILED BREAKDOWN:")
    print(f"📊 JIT Bot:          ${jit_pnl:+.2f} | Trades: {len(jit_client.get_trade_history())}")
    print(f"📊 Trend Bot:        ${trend_pnl:+.2f} | Trades: {len(trend_client.get_trade_history())}")
    print(f"📊 Hedge Bot:        ${hedge_pnl:+.2f} | Trades: {len(hedge_client.get_trade_history())}")
    
    print(f"\n💼 POSITIONS:")
    for bot_name, client in [("JIT", jit_client), ("Trend", trend_client), ("Hedge", hedge_client)]:
        positions = client.get_positions()
        if positions:
            print(f"   {bot_name}: {positions}")
        else:
            print(f"   {bot_name}: No positions")
    
    print(f"\n🎯 Market: SOL-PERP @ ${jit_client.get_orderbook().bids[0][0]:.2f}")

if __name__ == "__main__":
    main()
