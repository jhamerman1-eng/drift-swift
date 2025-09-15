#!/usr/bin/env python3
"""
Test Helius RPC endpoint connectivity
"""

import asyncio
from solana.rpc.async_api import AsyncClient

async def test_helius_rpc():
    """Test Helius RPC endpoint"""
    rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
    ws_url = "wss://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
    
    print(f"Testing Helius RPC endpoint...")
    print(f"RPC URL: {rpc_url}")
    print(f"WS URL: {ws_url}")
    print("=" * 60)
    
    try:
        # Test HTTP RPC
        client = AsyncClient(rpc_url)
        
        # Test getting latest blockhash
        blockhash = await client.get_latest_blockhash()
        print(f"✅ Latest Blockhash: {blockhash.value.blockhash}")
        
        # Test getting slot
        slot = await client.get_slot()
        print(f"✅ Current Slot: {slot}")
        
        # Test getting version
        version = await client.get_version()
        print(f"✅ Solana Version: {version.value.solana_core}")
        
        print("\n🎉 Helius RPC endpoint is working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Helius RPC: {e}")
        return False
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_helius_rpc())
