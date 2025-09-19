#!/usr/bin/env python3
"""
Test RPC Failover System
Demonstrates the automatic failover between RPC endpoints when they error out.
"""

import asyncio
import logging
import time
from libs.rpc_manager import RPCManager, DEFAULT_RPC_CONFIG, load_rpc_config_from_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockRPCOperation:
    """Mock RPC operation that can simulate failures."""
    
    def __init__(self, should_fail: bool = False, failure_type: str = "error"):
        self.should_fail = should_fail
        self.failure_type = failure_type
        self.call_count = 0
    
    async def execute(self, *args, **kwargs):
        """Execute the mock operation."""
        self.call_count += 1
        
        if self.should_fail:
            if self.failure_type == "rate_limit":
                raise Exception("HTTP 429: Too Many Requests")
            elif self.failure_type == "timeout":
                raise asyncio.TimeoutError("Request timed out")
            else:
                raise Exception("Simulated RPC error")
        
        # Simulate successful operation
        await asyncio.sleep(0.1)
        return f"Success on attempt {self.call_count}"

async def test_rpc_failover():
    """Test the RPC failover system."""
    logger.info("Testing RPC Failover System")
    logger.info("=" * 50)
    
    # Create RPC manager
    rpc_manager = RPCManager()
    
    # Try to load from YAML file first, fallback to default config
    config = load_rpc_config_from_file()
    if config:
        rpc_manager.add_endpoints_from_config(config)
        logger.info("Loaded endpoints from YAML configuration file")
    else:
        rpc_manager.add_endpoints_from_config(DEFAULT_RPC_CONFIG)
        logger.info("Loaded endpoints from default configuration")
    
    # Start health monitoring
    rpc_manager.start_health_monitoring()
    
    logger.info(f"Loaded {len(rpc_manager.endpoints)} RPC endpoints")
    
    # Test 1: Normal operation
    logger.info("\n" + "=" * 30)
    logger.info("Test 1: Normal Operation")
    logger.info("=" * 30)
    
    try:
        result = await rpc_manager.execute_with_failover(
            "test_operation",
            MockRPCOperation(should_fail=False).execute
        )
        logger.info(f"✅ Normal operation result: {result}")
    except Exception as e:
        logger.error(f"❌ Normal operation failed: {e}")
    
    # Test 2: Simulate rate limiting on primary endpoint
    logger.info("\n" + "=" * 30)
    logger.info("Test 2: Rate Limiting Failover")
    logger.info("=" * 30)
    
    # Temporarily mark primary endpoint as rate limited
    if rpc_manager.endpoints:
        primary_endpoint = rpc_manager.endpoints[0]
        from libs.rpc_manager import RPCStatus
        await rpc_manager.update_endpoint_health(primary_endpoint, RPCStatus.RATE_LIMITED)
        logger.info(f"Marked {primary_endpoint.name} as rate limited")
    
    try:
        result = await rpc_manager.execute_with_failover(
            "test_operation",
            MockRPCOperation(should_fail=False).execute
        )
        logger.info(f"✅ Failover operation result: {result}")
        
        # Check which endpoint was used
        current_endpoint = rpc_manager.current_endpoint
        if current_endpoint:
            logger.info(f"✅ Operation completed on: {current_endpoint.name}")
        
    except Exception as e:
        logger.error(f"❌ Failover operation failed: {e}")
    
    # Test 3: Simulate consecutive failures
    logger.info("\n" + "=" * 30)
    logger.info("Test 3: Consecutive Failures")
    logger.info("=" * 30)
    
    # Mark multiple endpoints as failed
    for i, endpoint in enumerate(rpc_manager.endpoints[:2]):  # Mark first 2 as failed
        from libs.rpc_manager import RPCStatus
        await rpc_manager.update_endpoint_health(endpoint, RPCStatus.FAILED)
        logger.info(f"Marked {endpoint.name} as failed")
    
    try:
        result = await rpc_manager.execute_with_failover(
            "test_operation",
            MockRPCOperation(should_fail=False).execute
        )
        logger.info(f"✅ Recovery operation result: {result}")
        
        current_endpoint = rpc_manager.current_endpoint
        if current_endpoint:
            logger.info(f"✅ Operation completed on: {current_endpoint.name}")
        
    except Exception as e:
        logger.error(f"❌ Recovery operation failed: {e}")
    
    # Test 4: Get status summary
    logger.info("\n" + "=" * 30)
    logger.info("Test 4: Status Summary")
    logger.info("=" * 30)
    
    status = rpc_manager.get_status_summary()
    logger.info("RPC Manager Status:")
    logger.info(f"  Current Endpoint: {status['current_endpoint']}")
    logger.info(f"  Total Endpoints: {status['total_endpoints']}")
    logger.info(f"  Available Endpoints: {status['available_endpoints']}")
    logger.info(f"  Failover Count: {status['failover_count']}")
    
    logger.info("\nEndpoint Details:")
    for name, health in status['endpoints'].items():
        logger.info(f"  {name}:")
        logger.info(f"    Status: {health['status']}")
        logger.info(f"    Consecutive Failures: {health['consecutive_failures']}")
        logger.info(f"    Error Count: {health['error_count']}")
        logger.info(f"    Last Success: {health['last_success']}")
    
    logger.info("\n" + "=" * 50)
    logger.info("RPC Failover Test Complete")
    logger.info("=" * 50)

async def test_environment_switching():
    """Test switching between different environments."""
    logger.info("\nTesting Environment Switching")
    logger.info("=" * 50)
    
    # Test mainnet
    logger.info("Testing Mainnet Configuration:")
    mainnet_manager = RPCManager()
    mainnet_manager.add_endpoints_from_config(DEFAULT_RPC_CONFIG)
    
    mainnet_endpoints = [ep.name for ep in mainnet_manager.endpoints]
    logger.info(f"Mainnet endpoints: {mainnet_endpoints}")
    
    # Test devnet
    logger.info("\nTesting Devnet Configuration:")
    devnet_manager = RPCManager()
    devnet_manager.add_endpoints_from_config(DEFAULT_RPC_CONFIG)
    
    devnet_endpoints = [ep.name for ep in devnet_manager.endpoints]
    logger.info(f"Devnet endpoints: {devnet_endpoints}")
    
    # Verify your Alchemy endpoints are included
    alchemy_endpoints = [ep for ep in devnet_manager.endpoints if 'alchemy' in ep.name.lower()]
    logger.info(f"\nYour Alchemy endpoints:")
    for ep in alchemy_endpoints:
        logger.info(f"  {ep.name}: {ep.http_url}")

async def main():
    """Main test function."""
    try:
        # Test basic failover functionality
        await test_rpc_failover()
        
        # Test environment switching
        await test_environment_switching()
        
        logger.info("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
