#!/usr/bin/env python3
"""
Swift Configuration Verification Script
Tests SWIFT_FORWARD_BASE configuration and sidecar health
"""

import os
import sys
import time
import requests
from typing import Dict, Any

def test_sidecar_configuration():
    """Test Swift sidecar configuration and health"""
    print("🔧 Testing Swift MM Bot Configuration...")

    # Check environment variables
    swift_forward_base = os.getenv("SWIFT_FORWARD_BASE", "").strip()
    port = os.getenv("PORT", "8787")

    print(f"📋 SWIFT_FORWARD_BASE: {swift_forward_base or 'NOT SET'}")
    print(f"📋 PORT: {port}")

    if not swift_forward_base:
        print("❌ SWIFT_FORWARD_BASE is not configured!")
        print("❌ Sidecar will run in LOCAL_ACK mode (stub)")
        print("❌ This is NOT suitable for production trading")
        print("📝 Set SWIFT_FORWARD_BASE=https://swift.drift.trade (mainnet)")
        print("📝 Or SWIFT_FORWARD_BASE=https://beta.drift.trade (devnet)")
        return False

    # Test sidecar health
    health_url = f"http://localhost:{port}/health"
    try:
        print(f"🔍 Testing sidecar health at: {health_url}")
        response = requests.get(health_url, timeout=5)
        health_data = response.json()

        print(f"✅ Sidecar responding: {response.status_code}")
        print(f"📊 Mode: {health_data.get('mode', 'unknown')}")
        print(f"🌐 Forward: {health_data.get('forward', 'none')}")

        if health_data.get('mode') == 'forward':
            print("✅ Sidecar is in FORWARD mode - PRODUCTION READY")
            return True
        else:
            print("⚠️  Sidecar is in LOCAL_ACK mode - NOT PRODUCTION READY")
            print("🔧 Configure SWIFT_FORWARD_BASE environment variable")
            return False

    except requests.RequestException as e:
        print(f"❌ Sidecar not responding: {e}")
        print("🔧 Make sure sidecar is running: npm start (in services/swift-mm/)")
        return False

def main():
    """Main verification function"""
    print("=" * 60)
    print("🚀 Swift MM Bot Configuration Verification")
    print("=" * 60)

    success = test_sidecar_configuration()

    print("\n" + "=" * 60)
    if success:
        print("✅ CONFIGURATION VERIFIED - Ready for production trading")
        return 0
    else:
        print("❌ CONFIGURATION ISSUES - Fix before production deployment")
        print("\n📋 Quick Fix:")
        print("1. Copy drift_v1_17_env.example to .env")
        print("2. Set SWIFT_FORWARD_BASE=https://swift.drift.trade")
        print("3. Restart sidecar and bot")
        return 1

if __name__ == "__main__":
    sys.exit(main())
