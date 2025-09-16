#!/usr/bin/env python3
"""
Quick test to verify environment configuration is working
"""
import os
from libs.config.environment import get_environment_config

# Set environment explicitly
os.environ["DRIFT_ENVIRONMENT"] = "devnet"

print("🔍 Testing Environment Configuration")
print(f"DRIFT_ENVIRONMENT = {os.environ.get('DRIFT_ENVIRONMENT', 'NOT SET')}")

# Load environment config
env_config = get_environment_config()

print(f"✅ Environment: {env_config.get_environment()}")
print(f"🌐 Use Local Sidecar: {env_config.use_local_sidecar()}")

# Get Swift config
swift_config = env_config.get_swift_config()
print(f"🚀 Swift Base URL: {swift_config['base_url']}")
print(f"🌐 Swift WS URL: {swift_config['ws_url']}")

# Verify expected values
expected_url = "https://master.swift.drift.trade"
actual_url = swift_config['base_url']

if actual_url == expected_url:
    print("✅ SUCCESS: Environment configuration is working correctly!")
else:
    print(f"❌ FAILED: Expected {expected_url}, got {actual_url}")
