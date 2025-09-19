#!/usr/bin/env python3
"""
Environment Configuration Manager

This script demonstrates how to properly set and validate environments.

Usage:
    python scripts/set_environment.py local    # Local dev with mock sidecar
    python scripts/set_environment.py devnet   # Devnet with real Swift API
    python scripts/set_environment.py mainnet  # Production mainnet
    
Or set via environment variable:
    export DRIFT_ENVIRONMENT=mainnet
    python run_swift_mm_complete.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from libs.config.environment import get_environment_config

def main():
    if len(sys.argv) != 2:
        print("Usage: python set_environment.py <local|devnet|mainnet>")
        print("")
        print("Available environments:")
        print("  local   - Local development with mock sidecar")
        print("  devnet  - Devnet testing with real Swift API") 
        print("  mainnet - Production mainnet trading")
        sys.exit(1)
    
    environment = sys.argv[1].lower()
    
    try:
        # Test the environment configuration
        env_config = get_environment_config(environment)
        
        print(f"🌍 Environment: {environment.upper()}")
        print(f"📝 Description: {env_config.get_description()}")
        print("")
        
        # Validate configuration
        validation = env_config.validate_configuration()
        if validation["valid"]:
            print("✅ Environment configuration is VALID")
        else:
            print("❌ Environment configuration has ISSUES:")
            for issue in validation["issues"]:
                print(f"   - {issue}")
            sys.exit(1)
        
        print("")
        print("📊 Configuration Summary:")
        summary = validation["config_summary"]
        print(f"   Drift Environment: {summary['drift_env']}")
        print(f"   RPC URL: {summary['rpc_url'][:50]}...")
        print(f"   Swift Enabled: {summary['swift_enabled']}")
        print(f"   Swift URL: {summary['swift_url']}")
        print(f"   Use Local Sidecar: {summary['use_local_sidecar']}")
        print(f"   JIT Enabled: {summary['jit_enabled']}")
        print(f"   JIT URL: {summary['jit_url']}")
        
        print("")
        if environment == "local":
            print("🧪 LOCAL ENVIRONMENT SETUP:")
            print("   1. Start local sidecar: cd services/jit-maker && npm start")
            print("   2. Run bot: python run_swift_mm_complete.py")
            print("   📝 All orders route to localhost:8787 (mock)")
            
        elif environment == "devnet":
            print("🌐 DEVNET ENVIRONMENT SETUP:")
            print("   1. Set environment: export DRIFT_ENVIRONMENT=devnet")
            print("   2. Run bot: python run_swift_mm_complete.py")
            print("   📝 Orders route to master.swift.drift.trade (real)")
            
        elif environment == "mainnet":
            print("🚀 MAINNET ENVIRONMENT SETUP:")
            print("   1. Set environment: export DRIFT_ENVIRONMENT=mainnet")
            print("   2. Run bot: python run_swift_mm_complete.py")
            print("   📝 Orders route to app.drift.trade (PRODUCTION)")
            print("   ⚠️  WARNING: REAL MONEY TRADING!")
        
        print("")
        print("🔧 To use this environment:")
        print(f"   export DRIFT_ENVIRONMENT={environment}")
        print("   python run_swift_mm_complete.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()



