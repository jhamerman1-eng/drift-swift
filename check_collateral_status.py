#!/usr/bin/env python3
"""Check Drift collateral status"""
import asyncio
from libs.drift.client import DriftpyClient
import yaml

async def check_collateral():
    try:
        # Load config
        with open('configs/core/drift_client.yaml') as f:
            cfg = yaml.safe_load(f)

        print("🔗 Initializing Drift client...")
        client = DriftpyClient(cfg)
        await client.initialize()

        print("📊 Checking user account...")
        # Check user account
        user_account = await client.drift_client.get_user_account()
        if user_account:
            print(f"✅ User account found: {user_account.authority}")
            collateral = await client.drift_client.get_collateral()
            print(f"💰 Collateral: {collateral} USD")
        else:
            print("❌ No user account found - need to deposit collateral at https://beta.drift.trade/~dev")

        await client.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_collateral())
