#!/usr/bin/env python3
"""
Simple test to see if the dashboard works
"""

print("🚀 Testing dashboard...")

try:
    from libs.drift.client import EnhancedMockDriftClient
    print("✅ Import successful")
    
    # Create a client
    client = EnhancedMockDriftClient("SOL-PERP", start=150.0)
    print("✅ Client created")
    
    # Get PnL
    pnl = client.get_pnl_summary()
    print(f"✅ PnL: ${pnl['total_pnl']:.2f}")
    
    print("🎉 Everything works! Dashboard should run now.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
