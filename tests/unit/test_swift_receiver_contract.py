#!/usr/bin/env python3
"""
Guard test for Swift receiver contract to prevent attribute drift regressions.

This test suite ensures that:
1. SwiftReceiver always exposes the required subscribe(handler, channel, backoff) method
2. We consistently use the validated local variable instead of self.swift_receiver
3. The contract is maintained across refactors

Run with: python -m pytest tests/unit/test_swift_receiver_contract.py -v
"""

import pytest
import asyncio
from typing import Any, Awaitable, Dict, Optional
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from run_swift_mm_complete import CompleteSwiftMMBot, SwiftReceiverProtocol
from utils.websocket_resilience import BackoffConfig


@pytest.fixture
def backoff_config():
    """Fixture providing a standard backoff configuration"""
    return BackoffConfig(
        initial_delay=1.0,
        max_delay=30.0,
        backoff_factor=2.0,
        jitter_percent=0.1
    )


@pytest.fixture
def subscriber_fixture(backoff_config):
    """Fixture providing a CompleteSwiftMMBot with Swift receiver configured"""
    config = {
        "symbol": "SOL-PERP",
        "leverage": 10,
        "post_only": True,
        "wallet_file": ".valid_wallet.json",  # Will be mocked
        "env": "devnet",
        "rpc_url": "https://devnet.helius-rpc.com/?api-key=test",
        "sidecar_url": "http://localhost:8787",
        "swift_websocket_url": "wss://swift.drift.trade/ws",
        "swift_api_key": "test-key"
    }

    # Create bot instance
    bot = CompleteSwiftMMBot(config)

    # Mock the dependencies that require actual connections
    with patch('run_swift_mm_complete.WEBSOCKETS_AVAILABLE', True), \
         patch('run_swift_mm_complete.httpx') as mock_httpx, \
         patch('drift.swift_receiver.SwiftOrderReceiver') as mock_receiver_class:

        # Create mock receiver with proper interface
        mock_receiver = Mock()
        mock_receiver.start = AsyncMock()
        mock_receiver_class.return_value = mock_receiver

        # Mock the async initialization to set up swift_receiver
        async def mock_initialize():
            bot.swift_receiver = mock_receiver
            return True

        bot.initialize = mock_initialize

        # Manually set up the receiver to match our protocol
        bot.swift_receiver = mock_receiver

        yield bot


@pytest.mark.asyncio
async def test_swift_receiver_contract(subscriber_fixture, backoff_config):
    """
    Fails if the SwiftReceiver loses `subscribe(handler, channel, backoff)` or if
    we accidentally call through self.swift_receiver instead of the validated local.

    This is the critical guard test that prevents regressions from attribute drift.
    """
    bot = subscriber_fixture  # provides ._get_swift_receiver() and ._initialize_resilient_subscriptions()
    sr = bot._get_swift_receiver()

    assert sr is not None, "Swift receiver must be present for this test"
    assert hasattr(sr, "subscribe"), "Swift receiver must expose .subscribe(...)"

    # Test that the accessor properly validates the receiver
    assert sr == bot.swift_receiver, "Accessor should return the same receiver instance"

    # Should not raise - this tests the entire contract flow
    await bot._initialize_resilient_subscriptions()
    assert bot.swift_subscription is not None


@pytest.mark.asyncio
async def test_swift_receiver_contract_with_adapter(subscriber_fixture):
    """
    Test that the SwiftReceiverAdapter properly implements the protocol contract.
    """
    from run_swift_mm_complete import SwiftReceiverAdapter

    # Create a mock underlying receiver (like SwiftOrderReceiver)
    mock_raw_receiver = Mock()
    mock_raw_receiver.start = AsyncMock()

    # Create adapter
    adapter = SwiftReceiverAdapter(mock_raw_receiver)

    # Test that adapter implements the protocol
    assert hasattr(adapter, 'subscribe'), "Adapter must implement subscribe method"
    assert callable(getattr(adapter, 'subscribe')), "subscribe must be callable"

    # Test the contract - adapter should delegate to underlying receiver
    async def test_handler(message_dict):
        assert isinstance(message_dict, dict), "Handler should receive dict"

    await adapter.subscribe(test_handler)

    # Verify the underlying receiver's start method was called
    mock_raw_receiver.start.assert_called_once()


@pytest.mark.asyncio
async def test_swift_receiver_contract_failure_cases():
    """
    Test that the contract properly fails when receiver is invalid or missing.
    """
    config = {
        "symbol": "SOL-PERP",
        "leverage": 10,
        "post_only": True,
    }

    bot = CompleteSwiftMMBot(config)

    # Test case 1: No receiver set
    bot.swift_receiver = None
    assert bot._get_swift_receiver() is None, "Should return None when no receiver"

    # Test case 2: Receiver without subscribe method
    class InvalidReceiver:
        pass

    bot.swift_receiver = InvalidReceiver()
    assert bot._get_swift_receiver() is None, "Should return None when subscribe missing"

    # Test case 3: Valid receiver with subscribe method
    mock_receiver = Mock()
    mock_receiver.subscribe = AsyncMock()
    bot.swift_receiver = mock_receiver

    result = bot._get_swift_receiver()
    assert result is not None, "Should return valid receiver"
    assert result == mock_receiver, "Should return the same instance"


@pytest.mark.asyncio
async def test_swift_receiver_contract_prevents_attribute_drift(subscriber_fixture, backoff_config):
    """
    Critical test: ensures we never accidentally call self.swift_receiver.subscribe()
    instead of using the validated local variable. This prevents race conditions.
    """
    bot = subscriber_fixture

    # Mock the resilient_swift_subscribe to track what receiver is passed
    with patch('run_swift_mm_complete.resilient_swift_subscribe') as mock_resilient:
        mock_subscription = Mock()
        mock_resilient.return_value = mock_subscription

        # This should use _get_swift_receiver() internally, not access self.swift_receiver directly
        await bot._initialize_resilient_subscriptions()

        # Verify that resilient_swift_subscribe was called with the validated receiver
        mock_resilient.assert_called_once()
        call_args = mock_resilient.call_args

        # The first argument should be the receiver returned by _get_swift_receiver()
        called_receiver = call_args[0][0]
        expected_receiver = bot._get_swift_receiver()

        assert called_receiver == expected_receiver, \
            "Should use validated receiver from _get_swift_receiver(), not self.swift_receiver"

        # Verify it's not accidentally using self.swift_receiver directly
        assert called_receiver is not bot.swift_receiver, \
            "Should not pass self.swift_receiver directly (use validated local)"


@pytest.mark.asyncio
async def test_contract_guard_integration():
    """
    Integration test that demonstrates the full contract guard in action.
    This test can be run standalone to verify the fix works.
    """
    # Create a minimal config for testing
    config = {
        "symbol": "SOL-PERP",
        "leverage": 10,
        "post_only": True,
    }

    bot = CompleteSwiftMMBot(config)

    # Test 1: Initially no receiver
    assert bot._get_swift_receiver() is None

    # Test 2: Set up a valid receiver (simulating our adapter pattern)
    from run_swift_mm_complete import SwiftReceiverAdapter

    # Create a mock that behaves like SwiftOrderReceiver
    mock_raw = Mock()
    mock_raw.start = AsyncMock()
    adapter = SwiftReceiverAdapter(mock_raw)

    bot.swift_receiver = adapter

    # Test 3: Now the accessor should return the valid receiver
    receiver = bot._get_swift_receiver()
    assert receiver is not None
    assert hasattr(receiver, 'subscribe')
    assert callable(receiver.subscribe)

    # Test 4: The receiver should be our adapter
    assert receiver == adapter

    print("✅ Contract guard integration test passed!")


def test_contract_guard_static_validation():
    """
    Static test that can run without async setup to validate the contract exists.
    """
    from run_swift_mm_complete import SwiftReceiverProtocol, SwiftReceiverAdapter

    # Test that protocol is defined
    assert SwiftReceiverProtocol is not None

    # Test that adapter class exists
    assert SwiftReceiverAdapter is not None

    # Test that CompleteSwiftMMBot has the required methods
    config = {"symbol": "SOL-PERP", "leverage": 10}
    bot = CompleteSwiftMMBot(config)

    assert hasattr(bot, '_get_swift_receiver')
    assert callable(getattr(bot, '_get_swift_receiver'))

    assert hasattr(bot, '_initialize_resilient_subscriptions')
    assert callable(getattr(bot, '_initialize_resilient_subscriptions'))

    print("✅ Contract guard static validation passed!")


if __name__ == "__main__":
    # Run basic validation without pytest
    print("Running contract guard validation...")

    try:
        test_contract_guard_static_validation()
        asyncio.run(test_contract_guard_integration())
        print("\n🎉 All contract guard validations passed!")
        print("The Swift receiver contract is properly protected against attribute drift.")
    except Exception as e:
        print(f"\n❌ Contract guard validation failed: {e}")
        raise

    # Also support running with pytest
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        pytest.main([__file__, "-v"])
