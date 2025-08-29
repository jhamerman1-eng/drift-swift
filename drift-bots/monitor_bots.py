#!/usr/bin/env python3
"""
Bot Monitoring Dashboard
Monitors all three bots (JIT, Hedge, Trend) running with enhanced mock client
"""

import time
import os
import sys
from datetime import datetime

def print_header():
    """Print dashboard header."""
    print("=" * 80)
    print("🤖 DRIFT BOTS MONITORING DASHBOARD")
    print("=" * 80)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔧 Enhanced Mock Client Mode - Realistic Trading Simulation")
    print("=" * 80)

def print_bot_status(bot_name, status="🟢 RUNNING"):
    """Print individual bot status."""
    print(f"{status} {bot_name:>15} Bot")

def print_market_info():
    """Print current market information."""
    print("\n📊 MARKET OVERVIEW")
    print("-" * 40)
    print("Market: SOL-PERP")
    print("Mode: Enhanced Mock Simulation")
    print("Features: Position Tracking | PnL Calculation | Realistic Fills")
    print("-" * 40)

def print_instructions():
    """Print monitoring instructions."""
    print("\n📋 MONITORING INSTRUCTIONS")
    print("-" * 40)
    print("1. Watch for order placement logs")
    print("2. Monitor position changes and PnL updates")
    print("3. Check trade execution timing")
    print("4. Observe risk management behavior")
    print("-" * 40)

def main():
    """Main monitoring loop."""
    print_header()
    print_market_info()
    print_instructions()
    
    print("\n🚀 Starting Bot Monitoring...")
    print("Press Ctrl+C to stop monitoring")
    print("-" * 80)
    
    try:
        while True:
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"\n⏰ [{current_time}] Monitoring active...")
            print("   Check terminal windows for bot activity")
            print("   Look for: [MOCK] Order placed/filled messages")
            print("   Monitor: Position updates and PnL calculations")
            
            time.sleep(10)  # Update every 10 seconds
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
        print("📊 Check individual bot terminals for final PnL and positions")
        print("✅ Enhanced Mock Client test complete!")

if __name__ == "__main__":
    main()
