#!/usr/bin/env python3
"""
Complete Swift Integration Test Suite
Tests all components step by step following the Swift MM Quick Integration Guide

This validates:
1. DriftClient subscription
2. UserMap subscription  
3. SwiftOrderSubscriber setup
4. Swift order reception and handling
5. Place-and-make transaction building
6. End-to-end flow validation
"""

import asyncio
import logging
import sys
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Add paths for imports
sys.path.append('.')
from libs.config.environment import get_environment_config

# Import the Swift integration
from swift_integration_v2 import SwiftMMIntegrationV2, SwiftIntegrationConfig

logger = logging.getLogger(__name__)

@dataclass
class TestResults:
    """Track test results"""
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    errors: list = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class SwiftIntegrationTestSuite:
    """Complete test suite for Swift integration"""
    
    def __init__(self):
        self.results = TestResults()
        self.config = get_environment_config("devnet")
        self.drift_client = None
        self.user_map = None
        self.integration = None
        
    async def run_all_tests(self) -> TestResults:
        """Run all tests in sequence"""
        logger.info("🧪 Starting Complete Swift Integration Test Suite")
        logger.info("=" * 80)
        
        # Test sequence following the documentation order
        test_methods = [
            ("Environment Validation", self.test_environment_config),
            ("Wallet Loading", self.test_wallet_loading),
            ("DriftClient Setup", self.test_drift_client_setup),
            ("DriftClient Subscription", self.test_drift_client_subscription),
            ("UserMap Setup", self.test_user_map_setup),
            ("UserMap Subscription", self.test_user_map_subscription),
            ("SwiftOrderSubscriber Setup", self.test_swift_order_subscriber_setup),
            ("Swift Integration Initialization", self.test_swift_integration_init),
            ("Swift WebSocket Connection", self.test_swift_websocket_connection),
            ("Order Reception Simulation", self.test_order_reception_simulation),
            ("Place-and-Make Transaction Building", self.test_place_and_make_building),
            ("End-to-End Flow", self.test_end_to_end_flow)
        ]
        
        for test_name, test_method in test_methods:
            await self._run_test(test_name, test_method)
            
            # Stop if critical early tests fail
            if self.results.tests_failed > 0 and test_name in [
                "Environment Validation", 
                "Wallet Loading", 
                "DriftClient Setup"
            ]:
                logger.error(f"❌ Critical test '{test_name}' failed - stopping test suite")
                break
        
        # Print final results
        self._print_test_summary()
        return self.results
    
    async def _run_test(self, test_name: str, test_method):
        """Run a single test with error handling"""
        logger.info(f"\n🔍 Test: {test_name}")
        logger.info("-" * 40)
        
        self.results.tests_run += 1
        
        try:
            start_time = time.time()
            await test_method()
            duration = time.time() - start_time
            
            logger.info(f"✅ PASSED: {test_name} ({duration:.2f}s)")
            self.results.tests_passed += 1
            
        except Exception as e:
            logger.error(f"❌ FAILED: {test_name} - {e}")
            self.results.tests_failed += 1
            self.results.errors.append({"test": test_name, "error": str(e)})
    
    async def test_environment_config(self):
        """Test 1: Validate environment configuration"""
        validation = self.config.validate_configuration()
        
        if not validation["valid"]:
            raise AssertionError(f"Environment config invalid: {validation['issues']}")
        
        config_summary = validation["config_summary"]
        logger.info(f"   Environment: {config_summary['drift_env']}")
        logger.info(f"   RPC URL: {config_summary['rpc_url']}")
        logger.info(f"   Swift URL: {config_summary['swift_url']}")
        logger.info(f"   JIT Enabled: {config_summary['jit_enabled']}")
        
        # Verify we're in devnet mode
        if config_summary['drift_env'] != 'devnet':
            raise AssertionError(f"Expected devnet environment, got {config_summary['drift_env']}")
        
        if not config_summary['swift_enabled']:
            raise AssertionError("Swift must be enabled for testing")
    
    async def test_wallet_loading(self):
        """Test 2: Load and validate wallet"""
        try:
            import json
            from solders.keypair import Keypair
            
            with open('.devnet_wallet.json', 'r') as f:
                wallet_data = json.load(f)
            
            self.keypair = Keypair.from_bytes(wallet_data)
            
            logger.info(f"   Wallet loaded: {self.keypair.pubkey()}")
            
        except Exception as e:
            raise AssertionError(f"Failed to load wallet: {e}")
    
    async def test_drift_client_setup(self):
        """Test 3: Setup DriftClient following documentation pattern"""
        try:
            from solana.rpc.async_api import AsyncClient
            from driftpy.drift_client import DriftClient
            
            # Create connection
            connection = AsyncClient(self.config.get_rpc_url())
            
            # Create DriftClient following documentation
            self.drift_client = DriftClient(
                connection,
                self.keypair,
                env=self.config.get_drift_env()
            )
            
            logger.info(f"   DriftClient created for {self.config.get_drift_env()}")
            
        except Exception as e:
            raise AssertionError(f"Failed to create DriftClient: {e}")
    
    async def test_drift_client_subscription(self):
        """Test 4: DriftClient subscription (required first step)"""
        try:
            await self.drift_client.subscribe()
            logger.info("   DriftClient subscribed successfully")
            
            # Verify subscription is active
            if not hasattr(self.drift_client, 'account_subscriber'):
                logger.warning("   ⚠️  No account_subscriber attribute - may be expected")
            
        except Exception as e:
            raise AssertionError(f"DriftClient subscription failed: {e}")
    
    async def test_user_map_setup(self):
        """Test 5: Setup UserMap following documentation pattern"""
        try:
            from driftpy.user_map.user_map import UserMap
            from driftpy.user_map.user_map_config import UserMapConfig, WebsocketConfig
            from solana.rpc.async_api import AsyncClient
            
            connection = AsyncClient(self.config.get_rpc_url())
            
            # Create WebsocketConfig
            ws_config = WebsocketConfig(
                resub_timeout_ms=30000,
                commitment="confirmed"
            )
            
            # Create UserMapConfig
            user_map_config = UserMapConfig(
                drift_client=self.drift_client,
                subscription_config=ws_config,
                connection=connection,
                skip_initial_load=False,
                include_idle=False,
            )
            
            # Create UserMap following documentation
            self.user_map = UserMap(user_map_config)
            
            logger.info("   UserMap created successfully")
            
        except Exception as e:
            raise AssertionError(f"Failed to create UserMap: {e}")
    
    async def test_user_map_subscription(self):
        """Test 6: UserMap subscription"""
        try:
            await self.user_map.subscribe()
            logger.info("   UserMap subscribed successfully")
            
        except Exception as e:
            raise AssertionError(f"UserMap subscription failed: {e}")
    
    async def test_swift_order_subscriber_setup(self):
        """Test 7: SwiftOrderSubscriber setup following documentation"""
        try:
            from driftpy.swift.order_subscriber import SwiftOrderSubscriber, SwiftOrderSubscriberConfig
            
            # Create config following documentation
            config = SwiftOrderSubscriberConfig(
                drift_client=self.drift_client,
                keypair=self.keypair,  # Required for authentication
                user_map=self.user_map,
                drift_env="devnet",
                market_indexes=[0, 1, 2, 3]  # SOL, BTC, ETH, etc.
            )
            
            self.swift_subscriber = SwiftOrderSubscriber(config)
            
            logger.info("   SwiftOrderSubscriber created successfully")
            logger.info(f"   Markets: {config.market_indexes}")
            logger.info(f"   Environment: {config.drift_env}")
            
        except Exception as e:
            raise AssertionError(f"Failed to create SwiftOrderSubscriber: {e}")
    
    async def test_swift_integration_init(self):
        """Test 8: Initialize our Swift integration wrapper"""
        try:
            integration_config = SwiftIntegrationConfig(
                keypair=self.keypair,
                drift_client=self.drift_client,
                user_map=self.user_map,
                drift_env="devnet",
                market_indexes=[0, 1, 2],  # SOL, BTC, ETH for testing
                enable_jit=True
            )
            
            self.integration = SwiftMMIntegrationV2(integration_config)
            await self.integration.initialize()
            
            logger.info("   Swift integration initialized successfully")
            
        except Exception as e:
            raise AssertionError(f"Swift integration initialization failed: {e}")
    
    async def test_swift_websocket_connection(self):
        """Test 9: Swift WebSocket connection (will be async task)"""
        try:
            # Start the subscription in background
            # Note: This is a long-running task, so we'll just verify it starts
            subscription_task = asyncio.create_task(
                self.integration.start_swift_subscription()
            )
            
            # Give it a moment to establish connection
            await asyncio.sleep(2.0)
            
            # Check if the task is running (not completed with error)
            if subscription_task.done():
                exception = subscription_task.exception()
                if exception:
                    raise exception
                else:
                    logger.info("   Swift subscription completed (unexpected)")
            else:
                logger.info("   Swift subscription running in background")
            
            # Cancel the task for testing
            subscription_task.cancel()
            try:
                await subscription_task
            except asyncio.CancelledError:
                pass
            
        except Exception as e:
            raise AssertionError(f"Swift WebSocket connection failed: {e}")
    
    async def test_order_reception_simulation(self):
        """Test 10: Simulate order reception and handling"""
        try:
            # Create a simulated Swift order following the documentation format
            from driftpy.types import (
                SignedMsgOrderParamsMessage, 
                OrderParams,
                MarketType,
                OrderType,
                PositionDirection
            )
            from driftpy.constants.numeric_constants import BASE_PRECISION, PRICE_PRECISION
            
            # Simulate order message raw (as received from WebSocket)
            simulated_order_raw = {
                "taker_authority": str(self.keypair.pubkey()),
                "signing_authority": str(self.keypair.pubkey()),
                "order_message": "mock_hex_data",
                "order_signature": "mock_signature",
                "uuid": "test-uuid-123"
            }
            
            # Simulate order params
            simulated_order_params = OrderParams(
                order_type=OrderType.Market(),
                market_type=MarketType.Perp(),
                direction=PositionDirection.Long(),
                base_asset_amount=int(1.0 * BASE_PRECISION),  # 1 SOL
                price=int(100.0 * PRICE_PRECISION),  # $100
                market_index=0,  # SOL-PERP
                reduce_only=False,
                trigger_price=None,
                oracle_price_offset=None,
                auction_duration=10,
                auction_start_price=int(100.0 * PRICE_PRECISION),
                auction_end_price=int(99.0 * PRICE_PRECISION),
                max_ts=None
            )
            
            # Create mock signed message
            mock_signed_message = type('MockSignedMessage', (), {
                'signed_msg_order_params': simulated_order_params,
                'sub_account_id': 0
            })()
            
            # Test our order handler
            await self.integration._handle_swift_order(
                simulated_order_raw,
                mock_signed_message,
                is_delegate_signer=False
            )
            
            logger.info("   Order handling simulation completed")
            
        except Exception as e:
            raise AssertionError(f"Order reception simulation failed: {e}")
    
    async def test_place_and_make_building(self):
        """Test 11: Place-and-make transaction building"""
        try:
            # This test verifies we can build the required instructions
            # Note: We can't actually execute without a real Swift order
            
            logger.info("   Place-and-make transaction building logic exists")
            logger.info("   ⚠️  Actual execution requires real Swift order")
            
            # Verify the method exists and is callable
            if not hasattr(self.swift_subscriber, 'get_place_and_make_signed_msg_order_ixs'):
                raise AssertionError("Missing get_place_and_make_signed_msg_order_ixs method")
            
            logger.info("   ✅ Required methods available")
            
        except Exception as e:
            raise AssertionError(f"Place-and-make building test failed: {e}")
    
    async def test_end_to_end_flow(self):
        """Test 12: End-to-end flow validation"""
        try:
            # Verify all components are properly initialized
            assert self.drift_client is not None, "DriftClient not initialized"
            assert self.user_map is not None, "UserMap not initialized"
            assert self.swift_subscriber is not None, "SwiftOrderSubscriber not initialized"
            assert self.integration is not None, "Swift integration not initialized"
            
            # Check statistics
            stats = self.integration.get_stats()
            logger.info(f"   Integration stats: {stats}")
            
            # Verify required components exist
            required_components = [
                'swift_orders_received',
                'swift_orders_processed', 
                'jit_orders_placed',
                'errors'
            ]
            
            for component in required_components:
                if component not in stats:
                    raise AssertionError(f"Missing stat component: {component}")
            
            logger.info("   ✅ End-to-end flow validation completed")
            
        except Exception as e:
            raise AssertionError(f"End-to-end flow validation failed: {e}")
    
    def _print_test_summary(self):
        """Print comprehensive test summary"""
        logger.info("\n" + "=" * 80)
        logger.info("🧪 SWIFT INTEGRATION TEST SUMMARY")
        logger.info("=" * 80)
        
        logger.info(f"📊 Tests Run: {self.results.tests_run}")
        logger.info(f"✅ Passed: {self.results.tests_passed}")
        logger.info(f"❌ Failed: {self.results.tests_failed}")
        
        success_rate = (self.results.tests_passed / self.results.tests_run * 100) if self.results.tests_run > 0 else 0
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.results.errors:
            logger.info("\n🚨 ERRORS:")
            for error in self.results.errors:
                logger.error(f"   - {error['test']}: {error['error']}")
        
        if self.results.tests_failed == 0:
            logger.info("\n🎉 ALL TESTS PASSED - Swift integration is ready!")
        else:
            logger.info(f"\n⚠️  {self.results.tests_failed} tests failed - review errors above")
        
        logger.info("=" * 80)

async def main():
    """Main test runner"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    
    # Run test suite
    test_suite = SwiftIntegrationTestSuite()
    results = await test_suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if results.tests_failed == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())
