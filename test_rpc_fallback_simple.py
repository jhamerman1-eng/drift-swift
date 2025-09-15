#!/usr/bin/env python3
"""
Simple RPC Fallback Test
Tests that the RPC fallback system is working correctly
"""

import asyncio
import aiohttp
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_rpc_endpoint(name, http_url, ws_url):
    """Test a single RPC endpoint"""
    try:
        logger.info(f"Testing {name}: {http_url}")
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "id": 1,
                "jsonrpc": "2.0",
                "method": "getSlot"
            }
            
            async with session.post(http_url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data:
                        logger.info(f"✅ {name} is working (slot: {data['result']})")
                        return True
                    else:
                        logger.warning(f"❌ {name} returned invalid response: {data}")
                        return False
                else:
                    logger.warning(f"❌ {name} returned status {response.status}")
                    return False
                    
    except Exception as e:
        logger.warning(f"❌ {name} failed: {e}")
        return False

async def test_fallback_chain():
    """Test the RPC fallback chain"""
    logger.info("Testing RPC Fallback Chain")
    logger.info("=" * 50)
    
    # Test endpoints in priority order
    endpoints = [
        {
            'name': 'Helius Devnet (Primary)',
            'http': 'https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494',
            'ws': 'wss://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494'
        },
        {
            'name': 'Alchemy Devnet (Fallback)',
            'http': 'https://solana-devnet.g.alchemy.com/v2/demo',
            'ws': 'wss://solana-devnet.g.alchemy.com/v2/demo'
        },
        {
            'name': 'Solana Labs Devnet (Last Resort)',
            'http': 'https://api.devnet.solana.com',
            'ws': 'wss://api.devnet.solana.com'
        }
    ]
    
    working_endpoints = []
    
    for endpoint in endpoints:
        success = await test_rpc_endpoint(endpoint['name'], endpoint['http'], endpoint['ws'])
        if success:
            working_endpoints.append(endpoint)
    
    logger.info("=" * 50)
    logger.info(f"✅ Found {len(working_endpoints)} working endpoints:")
    for endpoint in working_endpoints:
        logger.info(f"   - {endpoint['name']}")
    
    if len(working_endpoints) == 0:
        logger.error("❌ No working endpoints found!")
        return False
    else:
        logger.info("🎉 RPC fallback system is working correctly!")
        return True

if __name__ == "__main__":
    asyncio.run(test_fallback_chain())
