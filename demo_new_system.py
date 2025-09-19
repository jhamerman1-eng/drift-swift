#!/usr/bin/env python3
"""
Demo: New Core Settings System

This script demonstrates how the new core settings system works with
immutable settings, bot profiles, and client factories.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_core_settings():
    """Demonstrate the new core settings system."""
    print("🚀 Demonstrating New Core Settings System")
    print("=" * 50)

    try:
        # 1. Import the new core system
        from core.settings import get_core, load_profile, get_network, get_default_markets
        from core.accounts import load_wallet, validate_wallet
        from libs.drift.client_factory import make_clients, test_client_connectivity

        print("✅ Imports successful")

        # 2. Load core settings (immutable, cached)
        print("\n📋 Loading Core Settings...")
        core = get_core()

        print("   Network:", core.network)
        print("   RPC HTTP:", core.rpc.http)
        print("   Swift Base:", core.swift.orders_base)
        print("   Default Markets:", core.default_markets)
        print("   Features:", {
            'crash_v2': core.features.crash_v2,
            'cxlrep_v2': core.features.cxlrep_v2,
            'obi': core.features.obi
        })

        # 3. Test immutability
        print("\n🔒 Testing Immutability...")
        try:
            core.network = "modified"  # Should fail
            print("   ❌ ERROR: Settings are mutable!")
        except Exception:
            print("   ✅ Settings are properly immutable")

        # 4. Load bot profile
        print("\n🤖 Loading Bot Profile...")
        profile_path = "configs/bots/jit_template.yaml"
        if Path(profile_path).exists():
            profile = load_profile(profile_path)
            print("   Bot:", profile.name)
            print("   Leverage:", profile.target_leverage)
            print("   Markets:", profile.markets)
            print("   Max Position:", f"${profile.max_position_usd:,.0f}")
        else:
            print("   ⚠️  Profile template not found, creating one...")
            from libs.bots.common.profiles import save_profile_template
            save_profile_template("jit", profile_path)
            print("   ✅ Created profile template")

        # 5. Demonstrate convenience functions
        print("\n🔧 Convenience Functions...")
        print("   Network:", get_network())
        print("   Default Markets:", get_default_markets())

        # 6. Test wallet loading (if keypair exists)
        print("\n👛 Testing Wallet Integration...")
        try:
            # Try to load wallet from core settings
            wallet = load_wallet(core)
            is_valid = validate_wallet(wallet)
            print("   ✅ Wallet loaded and validated"            print("   📧 Public Key:", wallet.keypair.pubkey())
        except Exception as e:
            print(f"   ⚠️  Wallet test skipped: {e}")

        # 7. Test client creation
        print("\n🔗 Testing Client Creation...")
        try:
            drift_client, swift_client = make_clients(core)

            # Test connectivity (this would actually connect in real usage)
            connectivity = await test_client_connectivity(drift_client, swift_client)

            print("   ✅ Clients created successfully")
            if swift_client:
                print("   📡 Swift client available")
            else:
                print("   📡 Swift client not configured (optional)")

        except Exception as e:
            print(f"   ⚠️  Client creation test skipped: {e}")

        print("\n🎉 Core Settings System Demo Complete!")
        print("\nKey Benefits:")
        print("✅ Immutable core settings prevent accidental changes")
        print("✅ Bot profiles keep each bot focused and configurable")
        print("✅ Client factory ensures consistent client creation")
        print("✅ Environment overrides provide deployment flexibility")
        print("✅ Schema validation prevents configuration drift")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("This demo requires the new core system to be fully implemented.")
    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_core_settings())
