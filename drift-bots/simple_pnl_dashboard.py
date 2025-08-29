#!/usr/bin/env python3
"""
Simple PnL Dashboard - Shows current trading status and PnL for all bots
"""
import asyncio
import time
from libs.drift.client import EnhancedMockDriftClient

def create_mock_client(bot_name: str) -> EnhancedMockDriftClient:
    """Create a mock client for a specific bot"""
    return EnhancedMockDriftClient("SOL-PERP", start=150.0)

def display_bot_status(bot_name: str, client: EnhancedMockDriftClient):
    """Display status for a specific bot"""
    print(f"\n{'='*50}")
    print(f"🤖 {bot_name.upper()} BOT STATUS")
    print(f"{'='*50}")
    
    # Get current PnL and positions
    pnl = client.get_pnl_summary()
    positions = client.get_positions()
    
    print(f"💰 Total PnL: ${pnl['total_pnl']:.2f}")
    print(f"📈 Unrealized PnL: ${pnl['unrealized_pnl']:.2f}")
    print(f"💵 Realized PnL: ${pnl['realized_pnl']:.2f}")
    print(f"📊 Peak Equity: ${pnl['peak_equity']:.2f}")
    print(f"📉 Max Drawdown: ${pnl['max_drawdown']:.2f}")
    
    if positions:
        print(f"\n📋 Open Positions:")
        for pos in positions:
            side = "LONG" if pos.size > 0 else "SHORT"
            print(f"   {side}: {abs(pos.size):.2f} @ ${pos.avg_price:.2f}")
    else:
        print(f"\n📋 No open positions")
    
    # Get recent trades
    trades = client.get_trade_history()
    if trades:
        print(f"\n🔄 Recent Trades:")
        for trade in trades[-5:]:  # Last 5 trades
            side = "BUY" if trade.side == "buy" else "SELL"
            print(f"   {side}: {trade.size:.2f} @ ${trade.price:.2f}")
    else:
        print(f"\n🔄 No recent trades")

def main():
    """Main dashboard function"""
    print("🚀 DRIFT BOTS PnL DASHBOARD")
    print("="*50)
    
    # Create mock clients for each bot
    jit_client = create_mock_client("JIT")
    hedge_client = create_mock_client("HEDGE")
    trend_client = create_mock_client("TREND")
    
    try:
        while True:
            # Clear screen (Windows)
            import os
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("🚀 DRIFT BOTS PnL DASHBOARD")
            print("="*50)
            print(f"⏰ Last Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Display status for each bot
            display_bot_status("JIT Maker", jit_client)
            display_bot_status("Hedge", hedge_client)
            display_bot_status("Trend", trend_client)
            
            # Overall summary
            print(f"\n{'='*50}")
            print("📊 OVERALL SUMMARY")
            print(f"{'='*50}")
            
            total_pnl = (jit_client.get_pnl_summary()['total_pnl'] + 
                        hedge_client.get_pnl_summary()['total_pnl'] + 
                        trend_client.get_pnl_summary()['total_pnl'])
            
            print(f"💰 Total Portfolio PnL: ${total_pnl:.2f}")
            print(f"🤖 Active Bots: 3")
            print(f"📈 Status: Running with Enhanced Mock Client")
            
            print(f"\n🔄 Refreshing in 5 seconds... (Ctrl+C to stop)")
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Dashboard stopped by user")
        print("✅ Enhanced Mock Client provides realistic trading simulation")
        print("💡 Switch to Swift/DriftPy when ready for real trading")

if __name__ == "__main__":
    main()
