#!/usr/bin/env python3
"""
Test script to isolate JITConfig issue
"""

import sys
import os

# Add bots to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bots"))

from jit.main import JITConfig

def create_test_jit_config(**overrides):
    """Create a test JITConfig with default values"""
    defaults = {
        "symbol": "SOL-PERP",
        "leverage": 10,
        "post_only": True,
        "obi_microprice": True,
        "spread_bps_base": 8.0,
        "spread_bps_min": 4.0,
        "spread_bps_max": 25.0,
        "inventory_target": 0.0,
        "max_position_abs": 120.0,
        "cancel_replace_enabled": True,
        "cancel_replace_interval_ms": 1000,
        "toxicity_guard": True
    }
    defaults.update(overrides)
    print("Creating JITConfig with params:")
    for k, v in defaults.items():
        print(f"  {k}: {v} ({type(v).__name__})")
    return JITConfig(**defaults)

if __name__ == "__main__":
    try:
        print("Testing JITConfig creation...")
        config = create_test_jit_config(spread_bps_base=8.0, spread_bps_min=4.0, spread_bps_max=25.0)
        print("✅ JITConfig created successfully!")
        print(f"spread_bps_base: {config.spread_bps_base}")
        print(f"spread_bps_min: {config.spread_bps_min}")
        print(f"spread_bps_max: {config.spread_bps_max}")
    except Exception as e:
        print(f"❌ Error creating JITConfig: {e}")
        import traceback
        traceback.print_exc()
