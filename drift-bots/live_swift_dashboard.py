#!/usr/bin/env python3
"""
Live Swift PnL Dashboard - Shows real-time Swift trading activity
"""

import asyncio
import time
import os
from libs.drift.client import build_client_from_config, Order, OrderSide

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print dashboard header"""
    print("=" * 100)
    print("🚀 LIVE SWIFT PnL DASHBOARD - Real-Time Swift Trading")
    print("=" * 100)
    print(f"📅 {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔧 Swift API Integration | Real Order Placement | Live PnL Tracking")
    print("=" * 100)
    print()

def print_swift_status(client):
    """Print Swift driver status"""
    print("🔗 SWIFT DRIVER STATUS")
    print("-" * 40)
    print(f"✅ Driver Type: {type(client).__name__}")
    if hasattr(client, 'swift_base'):
        print(f"🌐 Swift API: {client.swift_base}")
        print(f"🔑 Keypair: {client.keypair_path}")
        print(f"📊 Market: {client.market}")
    print()

def print_trading_activity(client):
    """Print current trading activity"""
    print("📈 TRADING ACTIVITY")
    print("-" * 40)
    
    # Get orderbook
    ob = client.get_orderbook()
    if ob.bids and ob.asks:
        mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
        spread = ob.asks[0][0] - ob.bids[0][0]
        spread_bps = (spread / mid) * 10000
        
        print(f"🎯 Market: {client.market}")
        print(f"💰 Mid Price: ${mid:.4f}")
        print(f"📏 Spread: ${spread:.4f} ({spread_bps:.1f} bps)")
        print(f"📊 Top Bid: ${ob.bids[0][0]:.4f} (${ob.bids[0][1]:.1f})")
        print(f"📊 Top Ask: ${ob.asks[0][0]:.4f} (${ob.asks[0][1]:.1f})")
    
    print()

def print_positions_and_pnl(client):
    """Print positions and PnL"""
    print("💼 POSITIONS & PnL")
    print("-" * 40)
    
    try:
        # Get PnL summary
        pnl_summary = client.get_pnl_summary()
        print(f"💰 Total PnL:        ${pnl_summary['total_pnl']:+.2f}")
        print(f"📈 Unrealized PnL:   ${pnl_summary['unrealized_pnl']:+.2f}")
        print(f"💵 Realized PnL:     ${pnl_summary['realized_pnl']:+.2f}")
        print(f"📉 Max Drawdown:     ${pnl_summary['max_drawdown']:.2f}")
        print(f"🏆 Peak Equity:      ${pnl_summary['peak_equity']:.2f}")
        
        # Get positions
        positions = client.get_positions()
        if positions:
            print(f"\n📊 Active Positions:")
            for market, pos in positions.items():
                if abs(pos.size) > 0.001:
                    print(f"   {market}: {pos.size:+.4f} SOL @ ${pos.avg_price:.2f}")
        else:
            print(f"\n📊 No active positions")
            
        # Get trade count
        trades = client.get_trade_history()
        print(f"\n📝 Total Trades: {len(trades)}")
        
    except Exception as e:
        print(f"❌ Error getting PnL: {e}")
    
    print()

def print_swift_orders(client):
    """Print recent Swift orders"""
    print("📋 RECENT SWIFT ORDERS")
    print("-" * 40)
    
    try:
        # Get recent trades
        trades = client.get_trade_history()
        if trades:
            print("🔄 Recent Fills:")
            for trade in trades[-5:]:  # Show last 5 trades
                print(f"   {trade.side.value.upper()} {trade.size_usd:.1f} @ ${trade.price:.4f} (ID: {trade.order_id})")
        else:
            print("⏳ No trades yet - waiting for fills...")
            
        print(f"\n📊 Order Status: Active market making via Swift API")
        
    except Exception as e:
        print(f"❌ Error getting trades: {e}")
    
    print()

def print_instructions():
    """Print user instructions"""
    print("💡 CONTROLS:")
    print("   • Press Ctrl+C to exit")
    print("   • Dashboard updates every 3 seconds")
    print("   • Shows real Swift API integration")
    print("   • Orders being placed via Swift")
    print()
    print("=" * 100)

async def main():
    """Main dashboard function"""
    print("🚀 Starting Live Swift PnL Dashboard...")
    print("📊 Connecting to Swift driver...")
    print()
    
    try:
        # Build client with Swift driver
        client = await build_client_from_config("configs/core/drift_client.yaml")
        
        print(f"✅ Connected to Swift driver: {type(client).__name__}")
        print("🔄 Starting live updates...")
        print()
        
        # Main dashboard loop
        while True:
            clear_screen()
            print_header()
            
            # Show all information
            print_swift_status(client)
            print_trading_activity(client)
            print_positions_and_pnl(client)
            print_swift_orders(client)
            print_instructions()
            
            # Wait before next update
            await asyncio.sleep(3)
            
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"\n❌ Error in dashboard: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'client' in locals():
            await client.close()
        print("🔒 Dashboard closed")

if __name__ == "__main__":
    asyncio.run(main())
