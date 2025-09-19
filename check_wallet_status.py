#!/usr/bin/env python3
import asyncio
import os
from libs.core.env import load_keypair
from solana.rpc.async_api import AsyncClient
from anchorpy import Wallet
from driftpy.drift_client import DriftClient
from driftpy.constants.config import configs

async def check_wallet():
    try:
        print("🔍 Checking wallet and account status...")

        # Load keypair
        kp = load_keypair()
        print(f'✅ Wallet loaded: {kp.pubkey()}')

        # Initialize client
        rpc_url = os.getenv('RPC_HTTP', 'https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494')
        wallet = Wallet(kp)

        client = DriftClient(
            connection=AsyncClient(rpc_url),
            wallet=wallet,
            env='devnet'
        )

        print("📡 Connecting to Drift client...")
        await client.subscribe()

        # Check user account
        try:
            user = client.get_user()
            print(f'✅ User account loaded')
            print(f'   User public key: {user.user_public_key}')
        except Exception as e:
            print(f'❌ Failed to load user account: {e}')
            return

        # Check collateral
        try:
            collateral = await user.get_total_collateral()
            print(f'💰 Total collateral: ${collateral:.2f}')
        except Exception as e:
            print(f'❌ Failed to get collateral: {e}')

        # Check free collateral
        try:
            free_collateral = await user.get_free_collateral()
            print(f'💸 Free collateral: ${free_collateral:.2f}')
        except Exception as e:
            print(f'❌ Failed to get free collateral: {e}')

        # Check positions
        try:
            positions = user.get_active_perp_positions()
            print(f'📊 Active positions count: {len(positions)}')
            for i, pos in enumerate(positions):
                print(f'   Position {i}: market {pos.market_index}, base_amount: {pos.base_asset_amount}, quote_asset_amount: {pos.quote_asset_amount}')
        except Exception as e:
            print(f'❌ Failed to get positions: {e}')

        # Check spot positions
        try:
            spot_positions = user.get_active_spot_positions()
            print(f'🪙 Active spot positions count: {len(spot_positions)}')
            for i, pos in enumerate(spot_positions):
                print(f'   Spot {i}: market {pos.market_index}, scaled_balance: {pos.scaled_balance}')
        except Exception as e:
            print(f'❌ Failed to get spot positions: {e}')

        # Check health
        try:
            health = await user.get_health()
            print(f'❤️  Account health: {health:.2f}%')
        except Exception as e:
            print(f'❌ Failed to get health: {e}')

        print("✅ Wallet status check complete")

    except Exception as e:
        print(f'❌ Error during wallet check: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_wallet())