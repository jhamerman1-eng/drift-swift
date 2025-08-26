#!/usr/bin/env python3
"""
Comprehensive PnL Dashboard for All Three Bots
Tracks JIT, Trend, and Hedge bots with individual breakdowns and top-line summary
"""

import asyncio
import time
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import yaml

# Import our enhanced mock client
from libs.drift.client import EnhancedMockDriftClient, Order, OrderSide

@dataclass
class BotPnL:
    """Individual bot PnL tracking"""
    name: str
    total_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_equity: float = 0.0
    positions: Dict[str, float] = None
    trade_count: int = 0
    last_update: float = 0.0
    
    def __post_init__(self):
        if self.positions is None:
            self.positions = {}

@dataclass
class PortfolioSummary:
    """Top-line portfolio summary across all bots"""
    total_pnl: float = 0.0
    total_unrealized: float = 0.0
    total_realized: float = 0.0
    total_max_drawdown: float = 0.0
    total_peak_equity: float = 0.0
    total_positions: Dict[str, float] = None
    total_trades: int = 0
    bot_count: int = 0
    
    def __post_init__(self):
        if self.total_positions is None:
            self.total_positions = {}

class ComprehensivePnLDashboard:
    """Dashboard that tracks PnL across all three bots"""
    
    def __init__(self):
        self.bots: Dict[str, BotPnL] = {
            "JIT": BotPnL("JIT"),
            "Trend": BotPnL("Trend"), 
            "Hedge": BotPnL("Hedge")
        }
        self.portfolio = PortfolioSummary()
        self.market_data = {}
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Print dashboard header"""
        print("=" * 100)
        print("🎯 COMPREHENSIVE PnL DASHBOARD - All Three Bots")
        print("=" * 100)
        print(f"📅 {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("🔧 Multi-Bot PnL Tracking | Position Aggregation | Portfolio Summary")
        print("=" * 100)
        print()
    
    def print_portfolio_summary(self):
        """Print top-line portfolio summary"""
        print("💰 PORTFOLIO SUMMARY (All Bots)")
        print("-" * 50)
        print(f"📊 Total PnL:        ${self.portfolio.total_pnl:+.2f}")
        print(f"📈 Unrealized PnL:   ${self.portfolio.total_unrealized:+.2f}")
        print(f"💵 Realized PnL:     ${self.portfolio.total_realized:+.2f}")
        print(f"📉 Max Drawdown:     ${self.portfolio.total_max_drawdown:.2f}")
        print(f"🏆 Peak Equity:      ${self.portfolio.total_peak_equity:.2f}")
        print(f"📝 Total Trades:     {self.portfolio.total_trades}")
        print(f"🤖 Active Bots:      {self.portfolio.bot_count}")
        print()
        
        if self.portfolio.total_positions:
            print("💼 AGGREGATED POSITIONS:")
            for market, net_size in self.portfolio.total_positions.items():
                if abs(net_size) > 0.001:  # Only show significant positions
                    print(f"   {market}: {net_size:+.4f} SOL")
            print()
    
    def print_bot_breakdown(self):
        """Print individual bot PnL breakdowns"""
        print("🤖 INDIVIDUAL BOT BREAKDOWNS")
        print("=" * 80)
        
        for bot_name, bot_data in self.bots.items():
            print(f"📊 {bot_name} BOT:")
            print(f"   💰 Total PnL:      ${bot_data.total_pnl:+.2f}")
            print(f"   📈 Unrealized:     ${bot_data.unrealized_pnl:+.2f}")
            print(f"   💵 Realized:       ${bot_data.realized_pnl:+.2f}")
            print(f"   📉 Max Drawdown:   ${bot_data.max_drawdown:.2f}")
            print(f"   🏆 Peak Equity:    ${bot_data.peak_equity:.2f}")
            print(f"   📝 Trades:         {bot_data.trade_count}")
            
            if bot_data.positions:
                print(f"   💼 Positions:")
                for market, size in bot_data.positions.items():
                    if abs(size) > 0.001:
                        print(f"      {market}: {size:+.4f} SOL")
            
            print(f"   ⏰ Last Update:    {time.strftime('%H:%M:%S', time.localtime(bot_data.last_update))}")
            print("-" * 40)
            print()
    
    def print_market_info(self):
        """Print current market information"""
        print("📊 MARKET STATE")
        print("-" * 30)
        if self.market_data:
            for market, data in self.market_data.items():
                print(f"🔸 {market}: ${data['mid']:.4f} (Spread: {data['spread']:.2f} bps)")
        else:
            print("⏳ Waiting for market data...")
        print()
    
    def print_instructions(self):
        """Print user instructions"""
        print("💡 CONTROLS:")
        print("   • Press Ctrl+C to exit")
        print("   • Dashboard updates every 3 seconds")
        print("   • Shows real-time PnL across all bots")
        print()
        print("=" * 100)
    
    def update_bot_data(self, bot_name: str, client: EnhancedMockDriftClient):
        """Update bot PnL data from mock client"""
        if bot_name not in self.bots:
            return
            
        bot = self.bots[bot_name]
        
        # Get PnL summary
        pnl_summary = client.get_pnl_summary()
        bot.total_pnl = pnl_summary['total_pnl']
        bot.unrealized_pnl = pnl_summary['unrealized_pnl']
        bot.realized_pnl = pnl_summary['realized_pnl']
        bot.max_drawdown = pnl_summary['max_drawdown']
        bot.peak_equity = pnl_summary['peak_equity']
        
        # Get positions
        positions = client.get_positions()
        bot.positions = {market: pos.size for market, pos in positions.items()}
        
        # Get trade count
        trades = client.get_trade_history()
        bot.trade_count = len(trades)
        
        # Update timestamp
        bot.last_update = time.time()
        
        # Update market data
        ob = client.get_orderbook()
        if ob.bids and ob.asks:
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
            spread_bps = ((ob.asks[0][0] - ob.bids[0][0]) / mid) * 10000
            self.market_data[client.market] = {
                'mid': mid,
                'spread': spread_bps
            }
    
    def calculate_portfolio_summary(self):
        """Calculate top-line portfolio summary from all bots"""
        self.portfolio.total_pnl = sum(bot.total_pnl for bot in self.bots.values())
        self.portfolio.total_unrealized = sum(bot.unrealized_pnl for bot in self.bots.values())
        self.portfolio.total_realized = sum(bot.realized_pnl for bot in self.bots.values())
        self.portfolio.total_max_drawdown = max(bot.max_drawdown for bot in self.bots.values())
        self.portfolio.total_peak_equity = max(bot.peak_equity for bot in self.bots.values())
        self.portfolio.total_trades = sum(bot.trade_count for bot in self.bots.values())
        self.portfolio.bot_count = len([bot for bot in self.bots.values() if bot.last_update > 0])
        
        # Aggregate positions across all bots
        self.portfolio.total_positions = {}
        for bot in self.bots.values():
            for market, size in bot.positions.items():
                if market not in self.portfolio.total_positions:
                    self.portfolio.total_positions[market] = 0.0
                self.portfolio.total_positions[market] += size
    
    async def run_dashboard(self):
        """Run the comprehensive PnL dashboard"""
        print("🚀 Starting Comprehensive PnL Dashboard...")
        print("📊 Tracking JIT, Trend, and Hedge bots...")
        print()
        
        # Initialize mock clients for each bot
        clients = {}
        try:
            # Create separate mock clients for each bot to simulate independent trading
            clients["JIT"] = EnhancedMockDriftClient("SOL-PERP", start=150.0)
            clients["Trend"] = EnhancedMockDriftClient("SOL-PERP", start=150.0)
            clients["Hedge"] = EnhancedMockDriftClient("SOL-PERP", start=150.0)
            
            print("✅ Mock clients initialized for all bots")
            print("🔄 Starting dashboard updates...")
            print()
            
            # Main dashboard loop
            while True:
                self.clear_screen()
                self.print_header()
                
                # Update data from all bots
                for bot_name, client in clients.items():
                    self.update_bot_data(bot_name, client)
                
                # Calculate portfolio summary
                self.calculate_portfolio_summary()
                
                # Display all information
                self.print_portfolio_summary()
                self.print_bot_breakdown()
                self.print_market_info()
                self.print_instructions()
                
                # Wait before next update
                await asyncio.sleep(3)
                
        except KeyboardInterrupt:
            print("\n🛑 Dashboard stopped by user")
        except Exception as e:
            print(f"\n❌ Error in dashboard: {e}")
        finally:
            # Clean up clients
            for client in clients.values():
                await client.close()
            print("🔒 All clients closed")

async def main():
    """Main entry point"""
    dashboard = ComprehensivePnLDashboard()
    await dashboard.run_dashboard()

if __name__ == "__main__":
    asyncio.run(main())
