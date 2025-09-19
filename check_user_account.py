#!/usr/bin/env python3
"""
Check if user account exists on devnet
"""

import asyncio
import json
import os
from solders.keypair import Keypair
from driftpy.drift_client import DriftClient
from solana.rpc.async_api import AsyncClient

async def check_user_account():
    """Check user account status with enhanced Beta.Drift debugging"""

    print("🔍 Checking user account status...")
    print(f"🔧 Environment: DRIFT_ENV={os.getenv('DRIFT_ENV', 'devnet')}")
    print(f"🔧 RPC URL: {os.getenv('RPC_URL', 'https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494')}")
    print(f"🔧 Swift URL: {os.getenv('SWIFT_SIDECAR_URL', 'http://localhost:8787')}")

    try:
        # Load wallet
        with open('.valid_wallet.json', 'r') as f:
            wallet_data = json.load(f)

        # Extract keypair bytes from wallet format
        if "keypair" in wallet_data:
            keypair_bytes = bytes(wallet_data["keypair"])
        else:
            keypair_bytes = bytes(wallet_data)

        keypair = Keypair.from_bytes(keypair_bytes)
        print(f"✅ Loaded wallet: {keypair.pubkey()}")

        # Create Drift client
        connection = AsyncClient("https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")
        drift_client = DriftClient(connection, keypair, "devnet")

        # Try to add user
        print("Adding user account...")
        try:
            await drift_client.add_user(0)
            print("✅ User account added successfully")
        except Exception as e:
            print(f"⚠️ User account add failed: {e}")

        # Subscribe
        await drift_client.subscribe()
        await asyncio.sleep(2)

        # Try to get user
        print("Getting user account...")
        try:
            user = drift_client.get_user()
            if user:
                print("✅ User account exists")
                print(f"   User public key: {user.user_public_key if hasattr(user, 'user_public_key') else 'N/A'}")
                print(f"   Sub account ID: {user.sub_account_id if hasattr(user, 'sub_account_id') else 'N/A'}")

                # Check collateral
                try:
                    collateral = user.get_free_collateral()
                    print(f"   Free collateral: {collateral}")
                except Exception as e:
                    print(f"   Collateral check failed: {e}")

            else:
                print("❌ User account is None")
        except Exception as e:
            print(f"❌ Failed to get user: {e}")

        # Check if user account exists on chain
        print("Checking user account on chain...")
        try:
            # Get user account public key
            from driftpy.addresses import get_user_account_public_key
            user_account_pubkey = get_user_account_public_key(
                drift_client.program_id,
                keypair.pubkey(),
                0  # sub_account_id
            )
            print(f"User account public key: {user_account_pubkey}")
            print(f"🔍 This should match 'taker_authority' in Swift envelope!")
            print(f"🔍 Wallet pubkey: {keypair.pubkey()}")
            print(f"🔍 User account: {user_account_pubkey}")
            print(f"🔍 Match: {str(keypair.pubkey()) == str(user_account_pubkey)}")

            # Check if account exists
            account_info = await connection.get_account_info(user_account_pubkey)
            if account_info.value:
                print("✅ User account exists on chain")
                print(f"   Lamports: {account_info.value.lamports}")
                print(f"   Owner: {account_info.value.owner}")
            else:
                print("❌ User account does NOT exist on chain")
                print("   You may need to initialize it first")

        except Exception as e:
            print(f"❌ Failed to check user account on chain: {e}")

    except Exception as e:
        print(f"❌ Check failed: {e}")
        import traceback
        traceback.print_exc()

async def test_sidecar_user_lookup():
    """Test if sidecar can find our user account"""
    import httpx

    print("\n🔍 Testing sidecar user account lookup...")

    try:
        # Load wallet and get user account public key
        with open('.valid_wallet.json', 'r') as f:
            wallet_data = json.load(f)

        if "keypair" in wallet_data:
            keypair_bytes = bytes(wallet_data["keypair"])
        else:
            keypair_bytes = bytes(wallet_data)

        keypair = Keypair.from_bytes(keypair_bytes)

        # Create minimal drift client to get program_id
        connection = AsyncClient("https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")
        drift_client = DriftClient(connection, keypair, "devnet")

        # Get user account public key
        from driftpy.addresses import get_user_account_public_key
        user_account_pubkey = get_user_account_public_key(
            drift_client.program_id,
            keypair.pubkey(),
            0  # sub_account_id
        )

        print(f"🔍 Testing user account: {user_account_pubkey}")
        print(f"🔍 Sidecar URL: http://localhost:8787")

        # Try to make a test request to see what the sidecar expects
        async with httpx.AsyncClient() as client:
            try:
                # Test basic health
                health_response = await client.get("http://localhost:8787/health")
                print(f"🔍 Sidecar health: {health_response.status_code}")
            except Exception as e:
                print(f"❌ Sidecar connection failed: {e}")
                print(f"💡 Make sure sidecar is running: docker-compose -f docker-compose.swift.yml up -d")
                print(f"🔍 Sidecar mode: {health_response.json()}")

                # Try to see if sidecar has any user endpoints
                # This is just for debugging - we know /orders is the main endpoint
                print(f"🔍 User account should be available at sidecar for validation")
                print(f"🔍 SOLUTION: Configure sidecar with correct devnet endpoint")
                print(f"🔍 Option 1: Set SWIFT_FORWARD_BASE=https://beta.drift.trade")
                print(f"🔍 Option 2: Unset SWIFT_FORWARD_BASE to run in local mode")

            except Exception as e:
                print(f"❌ Sidecar connection failed: {e}")
                print(f"💡 Make sure sidecar is running: docker-compose -f docker-compose.swift.yml up -d")

        await connection.close()

    except Exception as e:
        print(f"❌ Test failed: {e}")

async def fix_sidecar_config():
    """Fix sidecar configuration for devnet environment"""
    print("\n🔧 Fixing sidecar configuration for Beta.Drift devnet...")

    # Check current environment
    drift_env = os.getenv("DRIFT_ENV", "devnet")
    swift_forward_base = os.getenv("SWIFT_FORWARD_BASE", "")

    print(f"Current DRIFT_ENV: {drift_env}")
    print(f"Current SWIFT_FORWARD_BASE: {swift_forward_base}")

    # Set correct configuration for devnet
    if drift_env == "devnet":
        correct_base = "https://beta.drift.trade"
        if swift_forward_base != correct_base:
            print(f"❌ SWIFT_FORWARD_BASE incorrect for devnet")
            print(f"✅ Should be: {correct_base}")
            print(f"💡 Set environment variable: export SWIFT_FORWARD_BASE={correct_base}")
            print(f"💡 Or restart sidecar with: SWIFT_FORWARD_BASE={correct_base} docker-compose -f docker-compose.swift.yml up -d")
        else:
            print(f"✅ SWIFT_FORWARD_BASE is correct for devnet")

    # Check if sidecar needs restart
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8787/health")
            health = response.json()
            if health.get("mode") == "forward" and not health.get("upstream"):
                print(f"⚠️  Sidecar is in forward mode but upstream is empty")
                print(f"💡 This indicates SWIFT_FORWARD_BASE may not be set correctly")
                print(f"💡 Restart sidecar with proper environment variables")
    except Exception as e:
        print(f"❌ Could not check sidecar health: {e}")

if __name__ == "__main__":
    asyncio.run(check_user_account())
    asyncio.run(test_sidecar_user_lookup())
    asyncio.run(fix_sidecar_config())
