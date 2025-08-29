#!/usr/bin/env python3
"""
Live PnL Dashboard for Enhanced Mock Client
Shows real-time positions, PnL, and trading activity
"""

import time
import os
import sys
from datetime import datetime
import asyncio
from libs.drift.client import build_client_from_config

class LivePnLDashboard:
    def __init__(self):
        self.client = None
        self.last_trade_count = 0
        
    async def initialize(self):
        """Initialize the mock client."""
        try:
            self.client = await build_client_from_config("configs/core/drift_client.yaml")
            print("✅ Enhanced Mock Client initialized successfully!")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize client: {e}")
            return False
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Print dashboard header."""
        print("=" * 100)
        print("💰 LIVE PnL DASHBOARD - Enhanced Mock Client")
        print("=" * 100)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🔧 Real-time Position Tracking | PnL Calculation | Trade Monitoring")
        print("=" * 100)
    
    def print_market_info(self):
        """Print current market information."""
        if not self.client:
            return
            
        try:
            ob = self.client.get_orderbook()
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
            spread = ob.asks[0][0] - ob.bids[0][0]
            
            print(f"\n📊 MARKET STATE")
            print("-" * 50)
            print(f"Mid Price:     ${mid:.4f}")
            print(f"Spread:        ${spread:.4f} ({spread/mid*10000:.1f} bps)")
            print(f"Top Bid:       ${ob.bids[0][0]:.4f} (${ob.bids[0][1]:.1f})")
            print(f"Top Ask:       ${ob.asks[0][0]:.4f} (${ob.asks[0][1]:.1f})")
        except Exception as e:
            print(f"❌ Error getting market info: {e}")
    
    def print_positions(self):
        """Print current positions and PnL."""
        if not self.client:
            return
            
        try:
            positions = self.client.get_positions()
            pnl_summary = self.client.get_pnl_summary()
            
            print(f"\n💼 POSITIONS & PnL")
            print("-" * 50)
            
            if positions:
                total_position_value = 0
                for market, pos in positions.items():
                    if pos.size != 0:
                        # Calculate position value
                        current_price = self.client.mid
                        position_value = pos.size * current_price
                        total_position_value += abs(position_value)
                        
                        print(f"📈 {market}:")
                        print(f"   Size:        {pos.size:+.4f} SOL")
                        print(f"   Avg Price:   ${pos.avg_price:.4f}")
                        print(f"   Current:     ${current_price:.4f}")
                        print(f"   Unrealized:  ${pos.unrealized_pnl:+.2f}")
                        print(f"   Realized:    ${pos.realized_pnl:+.2f}")
                        print(f"   Position Val: ${position_value:+.2f}")
                        print()
            else:
                print("📭 No open positions")
            
            # Overall PnL Summary
            print(f"💰 PnL SUMMARY")
            print("-" * 30)
            print(f"Total PnL:      ${pnl_summary['total_pnl']:+.2f}")
            print(f"Unrealized:     ${pnl_summary['unrealized_pnl']:+.2f}")
            print(f"Realized:       ${pnl_summary['realized_pnl']:+.2f}")
            print(f"Max Drawdown:   ${pnl_summary['max_drawdown']:.2f}")
            print(f"Peak Equity:    ${pnl_summary['peak_equity']:.2f}")
            
        except Exception as e:
            print(f"❌ Error getting positions: {e}")
    
    def print_trading_activity(self):
        """Print recent trading activity."""
        if not self.client:
            return
            
        try:
            trades = self.client.get_trade_history()
            open_orders = self.client.open_orders
            
            print(f"\n📝 TRADING ACTIVITY")
            print("-" * 50)
            
            # Recent trades
            if trades:
                print(f"Recent Trades ({len(trades)} total):")
                for trade in trades[-5:]:  # Show last 5 trades
                    timestamp = time.strftime("%H:%M:%S", time.localtime(trade.timestamp))
                    pnl_impact = ""
                    if hasattr(trade, 'pnl_impact'):
                        pnl_impact = f" | PnL: ${trade.pnl_impact:+.2f}"
                    
                    print(f"  {timestamp} | {trade.side.upper()} ${trade.size_usd:.1f} @ ${trade.price:.4f}{pnl_impact}")
            else:
                print("📭 No trades yet")
            
            # Open orders
            if open_orders:
                print(f"\nOpen Orders ({len(open_orders)}):")
                for order_id, order in open_orders.items():
                    print(f"  {order_id}: {order.side.upper()} ${order.size_usd:.1f} @ ${order.price:.4f}")
            else:
                print("\n📭 No open orders")
                
        except Exception as e:
            print(f"❌ Error getting trading activity: {e}")
    
    def print_risk_metrics(self):
        """Print risk metrics."""
        if not self.client:
            return
            
        try:
            pnl_summary = self.client.get_pnl_summary()
            
            # Calculate additional risk metrics
            if pnl_summary['peak_equity'] > 0:
                current_drawdown_pct = (pnl_summary['max_drawdown'] / pnl_summary['peak_equity']) * 100
            else:
                current_drawdown_pct = 0
            
            print(f"\n⚠️  RISK METRICS")
            print("-" * 30)
            print(f"Current Drawdown: {current_drawdown_pct:.1f}%")
            print(f"Max Drawdown:     ${pnl_summary['max_drawdown']:.2f}")
            print(f"Peak Equity:      ${pnl_summary['peak_equity']:.2f}")
            
        except Exception as e:
            print(f"❌ Error getting risk metrics: {e}")
    
    def print_instructions(self):
        """Print user instructions."""
        print(f"\n📋 CONTROLS")
        print("-" * 30)
        print("Press Ctrl+C to stop monitoring")
        print("Dashboard updates every 2 seconds")
        print("Look for [MOCK] messages in other terminals")
    
    async def run_dashboard(self):
        """Run the live dashboard."""
        if not await self.initialize():
            return
        
        try:
            while True:
                self.clear_screen()
                self.print_header()
                self.print_market_info()
                self.print_positions()
                self.print_trading_activity()
                self.print_risk_metrics()
                self.print_instructions()
                
                # Check for new trades
                current_trades = len(self.client.get_trade_history())
                if current_trades > self.last_trade_count:
                    print(f"\n🎉 NEW TRADE DETECTED! Total trades: {current_trades}")
                    self.last_trade_count = current_trades
                
                await asyncio.sleep(2)  # Update every 2 seconds
                
        except KeyboardInterrupt:
            print("\n\n🛑 Dashboard stopped by user")
            if self.client:
                await self.client.close()
            print("✅ Enhanced Mock Client closed")

async def main():
    """Main function."""
    dashboard = LivePnLDashboard()
    await dashboard.run_dashboard()

if __name__ == "__main__":
    asyncio.run(main())
