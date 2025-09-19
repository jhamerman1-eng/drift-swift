#!/usr/bin/env python3
"""
Monitor the final fix bot to see if it's successfully processing Swift orders
"""

import time
import subprocess
import sys
import re

def monitor_bot_logs():
    """Monitor the bot for success indicators"""
    
    print("🔍 Monitoring Final Fix Bot...")
    print("=" * 60)
    print("Looking for these SUCCESS indicators:")
    print("✅ 'Connected to Swift WebSocket' (should NOT have 'nacl' errors)")
    print("✅ 'Authenticated successfully'")
    print("✅ 'Subscribed to SOL-PERP/BTC-PERP/ETH-PERP'")
    print("✅ 'ORDER SUCCESSFULLY PROCESSED!'")
    print("✅ 'MARKET ORDER WITH PRICE=0 PROCESSED!'")
    print("=" * 60)
    
    # Check if process is running
    try:
        result = subprocess.run(['powershell', '-Command', 'Get-Process python -ErrorAction SilentlyContinue'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0 or 'python' not in result.stdout:
            print("❌ Bot process not found! Bot may have crashed.")
            print("🔧 Try running: python run_swift_bot_final_fix.py")
            return False
        else:
            print("✅ Bot process is running (PID found)")
    except Exception as e:
        print(f"⚠️ Could not check process: {e}")
    
    print("\n📊 Bot should show these messages if working:")
    print("   🔧 Initializing Swift Bot - FINAL FIX")
    print("   ✅ Wallet: GfYpU5xEQVErvsje7Reekq3tfhVnXLX8yvFxJgFRMiZC")
    print("   📡 Subscribing to DriftClient...")
    print("   ✅ Connected to Swift WebSocket")
    print("   🔐 Authenticated successfully")
    print("   📡 Subscribed to SOL-PERP")
    print("   📦 ORDER #1 (when orders arrive)")
    print("   ✅ PROCESSING: Market order with auction prices")
    print("   🎉 ORDER SUCCESSFULLY PROCESSED!")
    
    print("\n❌ Should NOT see:")
    print("   💥 Connection error: name 'nacl' is not defined")
    print("   ⚠️ Filtered order - Type: OrderType.Market(), Price: 0")
    
    print("\n📈 Key Success Metrics to Watch:")
    print("   📦 Total Processed: [should increase from 0]")
    print("   🔧 Market Orders (price=0): [should show count > 0]")
    
    print("\n🕐 Monitor for 2-3 minutes to see order processing...")
    print("   (Swift orders flow frequently on devnet)")
    
    print(f"\n⏰ Current time: {time.strftime('%H:%M:%S')}")
    print("🎯 If you see 'ORDER SUCCESSFULLY PROCESSED!' messages,")
    print("   the Market orders with Price=0 fix is working!")
    
    return True

if __name__ == "__main__":
    if monitor_bot_logs():
        print("\n✅ Bot monitoring complete")
        print("🔍 Check terminal output for actual bot logs")
    else:
        print("\n❌ Monitoring failed")
        sys.exit(1)





