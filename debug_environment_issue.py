#!/usr/bin/env python3
"""
Debug why DEVNET environment is still using local sidecar
"""
import os
from libs.config.environment import get_environment_config

# Set the same environment variables as the bot
os.environ["DRIFT_ENV"] = "devnet"
os.environ["DRIFT_ENVIRONMENT"] = "devnet"  # Try both
os.environ["SWIFT_FORWARD_BASE"] = "https://beta.drift.trade"

print("🔍 Debugging Environment Configuration Issue")
print(f"DRIFT_ENV = {os.environ.get('DRIFT_ENV', 'NOT SET')}")
print(f"DRIFT_ENVIRONMENT = {os.environ.get('DRIFT_ENVIRONMENT', 'NOT SET')}")
print(f"SWIFT_FORWARD_BASE = {os.environ.get('SWIFT_FORWARD_BASE', 'NOT SET')}")

# Load environment config
env_config = get_environment_config()

print(f"\n✅ Environment: {env_config.get_environment()}")
print(f"🌐 Use Local Sidecar: {env_config.use_local_sidecar()}")

# Get Swift config
swift_config = env_config.get_swift_config()
print(f"🚀 Swift Base URL: {swift_config['base_url']}")
print(f"🌐 Swift WS URL: {swift_config['ws_url']}")
print(f"🔄 Use Local Sidecar (from swift config): {swift_config['use_local_sidecar']}")

# Debug the actual environment configuration being loaded
print(f"\n📋 Raw environment config:")
print(f"Environment data: {env_config.env_config}")

if env_config.use_local_sidecar():
    print("❌ PROBLEM: Bot thinks it should use LOCAL sidecar in DEVNET!")
    print("This should be FALSE for devnet environment")
else:
    print("✅ CORRECT: Bot should use external Swift API")


