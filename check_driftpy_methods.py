#!/usr/bin/env python3
"""
Check what methods are available in the current DriftPy installation
"""
import sys
sys.path.append('libs')

try:
    from driftpy.drift_client import DriftClient
    from driftpy.types import OrderParams, OrderType, PositionDirection
    from driftpy.accounts import get_perp_market_account
    print("✅ DriftPy imports successful")
    
    # Check available methods on DriftClient
    print("\n🔍 DriftClient methods:")
    methods = [method for method in dir(DriftClient) if not method.startswith('_')]
    for method in sorted(methods):
        if 'sign' in method.lower() or 'convert' in method.lower() or 'order' in method.lower():
            print(f"  - {method}")
            
    print("\n🔍 Looking for order signing methods:")
    for method in methods:
        if 'sign' in method.lower():
            print(f"  ✓ {method}")
            
    print("\n🔍 Looking for conversion methods:")
    for method in methods:
        if 'convert' in method.lower():
            print(f"  ✓ {method}")
            
except Exception as e:
    print(f"❌ Error checking DriftPy: {e}")
    print("Make sure driftpy is installed: pip install driftpy")



