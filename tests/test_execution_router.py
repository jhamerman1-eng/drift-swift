#!/usr/bin/env python3
"""
Comprehensive tests for ExecutionRouter

Tests the critical maker vs taker routing, flag enforcement,
cancel/replace logic, and error handling.
"""

import pytest
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.execution.router import ExecutionRouter, ExecIntent, OrderResult, ErrorType

class MockDriftClient:
    """Mock Drift client for testing"""
    
    def __init__(self):
        self.place_perp_order = AsyncMock(return_value="DRIFT_ORDER_123")
        self.cancel_order = AsyncMock(return_value=True)
        self.modify_order = AsyncMock(return_value="DRIFT_MODIFIED_123")

class MockSwiftClient:
    """Mock Swift client for testing"""
    
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.place_signed = AsyncMock()
        self.cancel_order = AsyncMock(return_value=True)
        self.replace_order = AsyncMock(return_value="SWIFT_REPLACED_123")
        
        if should_fail:
            self.place_signed.side_effect = Exception("Swift connection failed")
        else:
            self.place_signed.return_value = "SWIFT_ORDER_456"

class TestExecutionRouter(unittest.TestCase):
    """Test ExecutionRouter functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.drift_client = MockDriftClient()
        self.swift_client = MockSwiftClient()
        
        # Basic router with mocked clients
        self.router = ExecutionRouter(
            drift_client=self.drift_client,
            swift_client=self.swift_client,
            swift_enabled=True,
            max_retries=2
        )
        
        # Sample order parameters
        self.sample_params = {
            "price": 150.0,
            "base_asset_amount": 1.0,
            "direction": "buy"
        }
    
    async def test_maker_routes_to_drift_only(self):
        """Test that maker orders only go to Drift, never Swift"""
        result = await self.router.place(self.sample_params, ExecIntent.MAKER)
        
        # Should succeed via Drift
        self.assertTrue(result.success)
        self.assertEqual(result.driver, "drift")
        self.assertEqual(result.order_id, "DRIFT_ORDER_123")
        
        # Verify Drift was called with enforced flags
        self.drift_client.place_perp_order.assert_called_once()
        call_args = self.drift_client.place_perp_order.call_args[0][0]
        
        # Check that maker flags were enforced
        # Note: In test environment, we'll get boolean fallbacks
        self.assertFalse(call_args.get('immediate_or_cancel', True))
        
        # Verify Swift was never called
        self.swift_client.place_signed.assert_not_called()
    
    async def test_taker_tries_swift_first(self):
        """Test that taker orders try Swift first"""
        result = await self.router.place(self.sample_params, ExecIntent.TAKER)
        
        # Should succeed via Swift
        self.assertTrue(result.success)
        self.assertEqual(result.driver, "swift")
        self.assertEqual(result.order_id, "SWIFT_ORDER_456")
        
        # Verify Swift was called
        self.swift_client.place_signed.assert_called_once()
        
        # Verify Drift was not called (Swift succeeded)
        self.drift_client.place_perp_order.assert_not_called()
    
    async def test_taker_fallback_to_drift(self):
        """Test that taker orders fall back to Drift when Swift fails"""
        # Use failing Swift client
        failing_router = ExecutionRouter(
            drift_client=self.drift_client,
            swift_client=MockSwiftClient(should_fail=True),
            swift_enabled=True
        )
        
        result = await failing_router.place(self.sample_params, ExecIntent.TAKER)
        
        # Should succeed via Drift fallback
        self.assertTrue(result.success)
        self.assertEqual(result.driver, "drift")
        self.assertEqual(result.order_id, "DRIFT_ORDER_123")
        
        # Verify Swift was attempted but failed
        failing_router.swift.place_signed.assert_called_once()
        
        # Verify Drift was called as fallback
        self.drift_client.place_perp_order.assert_called_once()
        call_args = self.drift_client.place_perp_order.call_args[0][0]
        
        # Check that taker flags were enforced in fallback
        self.assertTrue(call_args.get('immediate_or_cancel', False))
    
    async def test_swift_disabled_routes_taker_to_drift(self):
        """Test that when Swift is disabled, takers go directly to Drift"""
        router_no_swift = ExecutionRouter(
            drift_client=self.drift_client,
            swift_client=self.swift_client,
            swift_enabled=False  # Disabled
        )
        
        result = await router_no_swift.place(self.sample_params, ExecIntent.TAKER)
        
        # Should succeed via Drift
        self.assertTrue(result.success)
        self.assertEqual(result.driver, "drift")
        
        # Verify Swift was never called
        self.swift_client.place_signed.assert_not_called()
        
        # Verify Drift was called directly
        self.drift_client.place_perp_order.assert_called_once()
    
    async def test_cancel_maker_uses_drift(self):
        """Test that maker cancels go to Drift"""
        result = await self.router.cancel("TEST_ORDER_123", ExecIntent.MAKER)
        
        self.assertTrue(result.success)
        self.assertEqual(result.driver, "drift")
        
        # Verify Drift cancel was called
        self.drift_client.cancel_order.assert_called_once_with("TEST_ORDER_123")
        
        # Verify Swift cancel was not called
        self.swift_client.cancel_order.assert_not_called()
    
    async def test_cancel_taker_uses_swift(self):
        """Test that taker cancels prefer Swift"""
        result = await self.router.cancel("TEST_ORDER_456", ExecIntent.TAKER)
        
        self.assertTrue(result.success)
        self.assertEqual(result.driver, "swift")
        
        # Verify Swift cancel was called
        self.swift_client.cancel_order.assert_called_once_with("TEST_ORDER_456")
        
        # Verify Drift cancel was not called
        self.drift_client.cancel_order.assert_not_called()
    
    async def test_replace_maker_uses_drift(self):
        """Test that maker replaces use Drift modify"""
        new_params = {"price": 151.0, "base_asset_amount": 1.5}
        
        result = await self.router.replace("TEST_ORDER_123", new_params, ExecIntent.MAKER)
        
        self.assertTrue(result.success)
        self.assertEqual(result.driver, "drift")
        self.assertEqual(result.order_id, "DRIFT_MODIFIED_123")
        
        # Verify Drift modify was called
        self.drift_client.modify_order.assert_called_once()
        
        # Check that maker flags were enforced in the new params
        call_args = self.drift_client.modify_order.call_args[0][1]
        self.assertFalse(call_args.get('immediate_or_cancel', True))
    
    async def test_replace_taker_uses_swift(self):
        """Test that taker replaces prefer Swift"""
        new_params = {"price": 149.0, "base_asset_amount": 0.8}
        
        result = await self.router.replace("TEST_ORDER_456", new_params, ExecIntent.TAKER)
        
        self.assertTrue(result.success)
        self.assertEqual(result.driver, "swift")
        self.assertEqual(result.order_id, "SWIFT_REPLACED_123")
        
        # Verify Swift replace was called
        self.swift_client.replace_order.assert_called_once()
    
    async def test_precision_normalization(self):
        """Test that price and quantity are normalized"""
        # Router with custom normalizers
        router_with_normalizers = ExecutionRouter(
            drift_client=self.drift_client,
            swift_client=self.swift_client,
            tick_normalizer=lambda p: round(p, 2),  # Round to 2 decimals
            lot_normalizer=lambda q: round(q, 3)    # Round to 3 decimals
        )
        
        params_with_precision = {
            "price": 150.123456,        # Should round to 150.12
            "base_asset_amount": 1.123456,  # Should round to 1.123
            "direction": "buy"
        }
        
        await router_with_normalizers.place(params_with_precision, ExecIntent.MAKER)
        
        # Check that normalized values were passed to Drift
        call_args = self.drift_client.place_perp_order.call_args[0][0]
        self.assertEqual(call_args["price"], 150.12)
        self.assertEqual(call_args["base_asset_amount"], 1.123)
    
    async def test_error_classification_and_retries(self):
        """Test error classification and retry logic"""
        # Mock Drift to fail with transient error first, then succeed
        self.drift_client.place_perp_order.side_effect = [
            Exception("Connection timeout"),  # Transient - should retry
            "DRIFT_ORDER_RETRY"              # Success on retry
        ]
        
        result = await self.router.place(self.sample_params, ExecIntent.MAKER)
        
        # Should succeed after retry
        self.assertTrue(result.success)
        self.assertEqual(result.order_id, "DRIFT_ORDER_RETRY")
        self.assertEqual(result.retry_count, 1)  # One retry happened
        
        # Verify it was called twice (initial + retry)
        self.assertEqual(self.drift_client.place_perp_order.call_count, 2)
    
    async def test_permanent_error_no_retry(self):
        """Test that permanent errors don't trigger retries"""
        # Mock Drift to fail with permanent error
        self.drift_client.place_perp_order.side_effect = Exception("Insufficient funds")
        
        result = await self.router.place(self.sample_params, ExecIntent.MAKER)
        
        # Should fail without retries
        self.assertFalse(result.success)
        self.assertEqual(result.error_type, ErrorType.PERMANENT)
        self.assertEqual(result.retry_count, 0)  # No retries
        
        # Verify it was only called once
        self.assertEqual(self.drift_client.place_perp_order.call_count, 1)
    
    async def test_metrics_tracking(self):
        """Test that metrics are properly tracked"""
        # Place a few orders
        await self.router.place(self.sample_params, ExecIntent.MAKER, context="refresh")
        await self.router.place(self.sample_params, ExecIntent.TAKER, context="jit_response")
        
        # Get metrics
        metrics = self.router.get_metrics()
        
        # Check that metrics were recorded
        self.assertIn("execution_stats", metrics)
        self.assertIn("config", metrics)
        
        # Check execution stats were populated
        stats = metrics["execution_stats"]
        self.assertIn("counters", stats)
        self.assertIn("timestamp", stats)
    
    def test_invalid_intent_rejected(self):
        """Test that invalid intents are rejected"""
        async def test_invalid():
            result = await self.router.place(self.sample_params, "INVALID_INTENT")
            self.assertFalse(result.success)
            self.assertEqual(result.error_type, ErrorType.PERMANENT)
        
        asyncio.run(test_invalid())

# Test runner functions for async tests
def run_async_test(test_func):
    """Helper to run async test functions"""
    return asyncio.run(test_func())

class TestAsyncMethods(TestExecutionRouter):
    """Async test wrapper"""
    
    def test_maker_routes_to_drift_only_sync(self):
        """Sync wrapper for async test"""
        run_async_test(self.test_maker_routes_to_drift_only)
    
    def test_taker_tries_swift_first_sync(self):
        """Sync wrapper for async test"""
        run_async_test(self.test_taker_tries_swift_first)
    
    def test_taker_fallback_to_drift_sync(self):
        """Sync wrapper for async test"""
        run_async_test(self.test_taker_fallback_to_drift)
    
    def test_swift_disabled_routes_taker_to_drift_sync(self):
        """Sync wrapper for async test"""
        run_async_test(self.test_swift_disabled_routes_taker_to_drift)
    
    def test_cancel_maker_uses_drift_sync(self):
        """Sync wrapper for async test"""
        run_async_test(self.test_cancel_maker_uses_drift)
    
    def test_cancel_taker_uses_swift_sync(self):
        """Sync wrapper for async test"""
        run_async_test(self.test_cancel_taker_uses_swift)
    
    def test_replace_maker_uses_drift_sync(self):
        """Sync wrapper for async test"""
        run_async_test(self.test_replace_maker_uses_drift)
    
    def test_replace_taker_uses_swift_sync(self):
        """Sync wrapper for async test"""
        run_async_test(self.test_replace_taker_uses_swift)
    
    def test_precision_normalization_sync(self):
        """Sync wrapper for async test"""
        run_async_test(self.test_precision_normalization)
    
    def test_error_classification_and_retries_sync(self):
        """Sync wrapper for async test"""
        run_async_test(self.test_error_classification_and_retries)
    
    def test_permanent_error_no_retry_sync(self):
        """Sync wrapper for async test"""
        run_async_test(self.test_permanent_error_no_retry)
    
    def test_metrics_tracking_sync(self):
        """Sync wrapper for async test"""
        run_async_test(self.test_metrics_tracking)

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
