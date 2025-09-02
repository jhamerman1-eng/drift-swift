#!/usr/bin/env python3
"""
Test RPC Health Check Script
Tests the RPC connectivity using the same method as the hedge bot.
"""

import asyncio
import logging
import aiohttp
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RPCTester:
    def __init__(self):
        self.rpc_health_cache = {}
        self.rpc_health_cache_time = 0
        self.rpc_health_cache_ttl = 300  # 5 minutes

    async def test_rpc_connectivity(self, rpc_options: list) -> dict:
        """Test RPC connectivity and return the first working endpoint."""
        # Check cache first
        current_time = time.time()
        if (self.rpc_health_cache and
            current_time - self.rpc_health_cache_time < self.rpc_health_cache_ttl):
            cached_result = self.rpc_health_cache.get('working_rpc')
            if cached_result:
                logger.info(f"[RPC] Using cached working RPC: {cached_result['name']}")
                return cached_result

        logger.info("[RPC] Testing RPC endpoint connectivity...")

        for rpc in rpc_options:
            try:
                logger.info(f"[RPC] Testing {rpc['name']}: {rpc['http']}")

                # Test HTTP connectivity with block production check
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "id": 1,
                        "jsonrpc": "2.0",
                        "method": "getBlockProduction"
                    }

                    async with session.post(rpc['http'],
                                          json=payload,
                                          timeout=aiohttp.ClientTimeout(total=5)) as response:

                        if response.status == 200:
                            data = await response.json()
                            if 'result' in data:
                                logger.info(f"[RPC] ✅ {rpc['name']} is working")
                                # Cache the result
                                self.rpc_health_cache = {'working_rpc': rpc}
                                self.rpc_health_cache_time = current_time
                                return rpc
                            else:
                                logger.warning(f"[RPC] ❌ {rpc['name']} returned invalid response")
                        else:
                            logger.warning(f"[RPC] ❌ {rpc['name']} returned status {response.status}")

            except Exception as e:
                logger.warning(f"[RPC] ❌ {rpc['name']} failed: {e}")

        logger.error("[RPC] ❌ No working RPC endpoints found")
        return None

    async def test_mainnet_endpoints(self):
        """Test mainnet RPC endpoints."""
        logger.info("Testing Mainnet RPC Endpoints...")
        logger.info("=" * 50)

        mainnet_options = [
            {
                'http': 'https://solana-mainnet.g.alchemy.com/v2/kjEqbEv7evHlXvQf4LZeU',
                'ws': 'wss://solana-mainnet.g.alchemy.com/v2/kjEqbEv7evHlXvQf4LZeU',
                'name': 'Alchemy (your key)'
            },
            {
                'http': 'https://api.mainnet-beta.solana.com',
                'ws': 'wss://api.mainnet-beta.solana.com',
                'name': 'Solana Labs'
            },
            {
                'http': 'https://solana-mainnet.g.alchemy.com/v2/demo',
                'ws': 'wss://solana-mainnet.g.alchemy.com/v2/demo',
                'name': 'Alchemy Demo'
            }
        ]

        working_rpc = await self.test_rpc_connectivity(mainnet_options)

        if working_rpc:
            logger.info("=" * 50)
            logger.info("✅ SUCCESS: Found working RPC endpoint!")
            logger.info(f"   Name: {working_rpc['name']}")
            logger.info(f"   HTTP: {working_rpc['http']}")
            logger.info(f"   WS: {working_rpc['ws']}")
            logger.info("=" * 50)
        else:
            logger.error("=" * 50)
            logger.error("❌ FAILURE: No working RPC endpoints found")
            logger.error("This may indicate network connectivity issues")
            logger.error("=" * 50)

    async def test_devnet_endpoints(self):
        """Test devnet RPC endpoints."""
        logger.info("Testing Devnet RPC Endpoints...")
        logger.info("=" * 50)

        devnet_options = [
            {
                'http': 'https://solana-devnet.g.alchemy.com/v2/demo',
                'ws': 'wss://solana-devnet.g.alchemy.com/v2/demo',
                'name': 'Alchemy Devnet'
            },
            {
                'http': 'https://api.devnet.solana.com',
                'ws': 'wss://api.devnet.solana.com',
                'name': 'Solana Labs Devnet'
            }
        ]

        working_rpc = await self.test_rpc_connectivity(devnet_options)

        if working_rpc:
            logger.info("=" * 50)
            logger.info("✅ SUCCESS: Found working devnet RPC endpoint!")
            logger.info(f"   Name: {working_rpc['name']}")
            logger.info(f"   HTTP: {working_rpc['http']}")
            logger.info(f"   WS: {working_rpc['ws']}")
            logger.info("=" * 50)
        else:
            logger.error("=" * 50)
            logger.error("❌ FAILURE: No working devnet RPC endpoints found")
            logger.error("=" * 50)

async def main():
    """Main test function."""
    tester = RPCTester()

    logger.info("RPC Health Check Test")
    logger.info("=" * 60)

    # Test mainnet first
    await tester.test_mainnet_endpoints()

    logger.info("")
    logger.info("Waiting 2 seconds before testing devnet...")
    await asyncio.sleep(2)

    # Test devnet
    await tester.test_devnet_endpoints()

    logger.info("")
    logger.info("RPC Health Check Complete")
    logger.info("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
