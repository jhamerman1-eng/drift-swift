#!/usr/bin/env python3
"""
Test script to check available markets on Drift devnet
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the libs directory to the path
sys.path.append(str(Path(__file__).parent / "libs"))

from drift.client import build_client_from_config

async def test_markets():
    """Test available markets on devnet"""
    print("🔍 Testing Drift Devnet Markets")
    print("=" * 40)
    
    # Set environment variables
    os.environ["DRIFT_HTTP_URL"] = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
    os.environ["DRIFT_WS_URL"] = "wss://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
    os.environ["DRIFT_KEYPAIR_PATH"] = "test_keypair.json"
    
    try:
        # Build client
        print("📡 Building Drift client...")
        client = await build_client_from_config("configs/core/drift_client.yaml")
        
        if not hasattr(client, 'drift_client') or not client.drift_client:
            print("❌ Drift client not initialized")
            return
        
        print("✅ Drift client initialized")
        
        # Test different market indices
        print("\n🔍 Testing market indices...")
        for idx in range(10):  # Test indices 0-9
            try:
                print(f"\n--- Testing Market Index {idx} ---")
                
                # Try to get market account
                try:
                    market_account = await client.drift_client.get_perp_market_account(idx)
                    print(f"✅ Market account {idx} found")
                    print(f"   Market name: {market_account.market_name}")
                    print(f"   Status: {market_account.status}")
                except Exception as e:
                    print(f"❌ Market account {idx} failed: {e}")
                
                # Try to get oracle price
                try:
                    oracle_data = client.drift_client.get_oracle_price_data_for_perp_market(idx)
                    oracle_price = client.drift_client.convert_to_number(oracle_data.price)
                    print(f"✅ Oracle price for market {idx}: ${oracle_price:.4f}")
                except Exception as e:
                    print(f"❌ Oracle price for market {idx} failed: {e}")
                
            except Exception as e:
                print(f"❌ Market index {idx} test failed: {e}")
        
        # Close client
        await client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_markets())
