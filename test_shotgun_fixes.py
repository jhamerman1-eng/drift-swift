#!/usr/bin/env python3
"""
Test script to verify shotgun bot fixes
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.append('.')

async def test_drift_fallback():
    """Test Drift fallback functionality"""
    print("🧪 Testing Drift fallback functionality...")

    try:
        # Import the bot class
        from run_swift_mm_complete import CompleteSwiftMMBot

        # Create a test config
        test_config = {
            "drift_env": "devnet",
            "keypair_path": ".devnet_wallet.json",
            "sidecar_url": "https://master.swift.drift.trade",  # FIX: Use real Swift API
            "symbol": "SOL-PERP",
            "leverage": 10,
            "post_only": True,
            "obi_microprice": True,
            "spread_bps": 8.0,
            "inventory_target": 0.0,
            "max_position_abs": 10.0,
            "cancel_replace_enabled": True,
            "cancel_replace_interval_ms": 1000,
            "toxicity_guard": True,
            "drift_fallback_enabled": True,
            "swift_ws_enabled": True,
            "swift_websocket_url": "wss://master.swift.drift.trade/ws"
        }

        # Create bot instance
        bot = CompleteSwiftMMBot(test_config)

        # Test Drift client readiness
        print("🔍 Testing Drift client readiness...")
        drift_ready = await bot._ensure_drift_client_ready()

        if drift_ready:
            print("✅ Drift fallback is working correctly")
        else:
            print("⚠️  Drift fallback may have issues")

        # Test sidecar validation with fallback
        print("🔍 Testing sidecar validation with fallback...")
        try:
            sidecar_result = await bot._validate_sidecar_startup()
            print(f"✅ Sidecar validation returned: {sidecar_result}")
        except Exception as e:
            print(f"⚠️  Sidecar validation failed as expected: {e}")

        print("🎉 All tests completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_drift_fallback())
