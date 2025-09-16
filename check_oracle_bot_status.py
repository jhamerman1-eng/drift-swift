#!/usr/bin/env python3
"""
Quick Oracle Bot Status Check
"""

import time
import subprocess
import sys

print("🔍 Oracle-Aware MM Bot Status Check")
print("=" * 50)

# Check if Python processes are running
try:
    result = subprocess.run(['powershell', '-Command', 'Get-Process python'], 
                          capture_output=True, text=True, timeout=5)
    if result.stdout:
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:  # Header + at least one process
            print(f"✅ Found {len(lines)-1} Python process(es) running")
        else:
            print("❌ No Python processes found")
    else:
        print("❌ No Python processes found")
except Exception as e:
    print(f"⚠️ Could not check processes: {e}")

print("\n📋 What should be happening:")
print("• Oracle-aware bot should be running")
print("• It will connect to Swift WebSocket")  
print("• Oracle orders (price=0) will now be ACCEPTED")
print("• You should see 'Oracle Order Received (VALID)' messages")
print("• Previous errors about 'Order has no price' should stop")

print("\n🎯 Key Fix Applied:")
print("• OLD: Oracle orders filtered out for having price=0")
print("• NEW: Oracle orders accepted (they use oracle_price_offset)")
print("• This fixes the main reason you weren't seeing Swift orders!")

print("\n⏰ Give it 2-3 minutes to show Oracle order processing...")
