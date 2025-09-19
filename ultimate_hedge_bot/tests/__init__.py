"""
Ultimate Hedge Bot - Testing Framework
Comprehensive testing suite for production-ready validation.
"""

import pytest
import asyncio
from typing import Dict, Any
import logging

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture."""
    return {
        'env': 'devnet',
        'rpc': {
            'http_url': 'https://api.devnet.solana.com',
            'timeout_seconds': 30
        },
        'hedge': {
            'max_inventory_usd': 1500.0,
            'max_position_abs': 100.0,
            'tick_size': 0.01
        },
        'risk': {
            'max_drawdown_pct': 0.1
        },
        'performance': {
            'target_latency_ms': 10
        },
        'use_mock_fallback': True  # Use mock clients for testing
    }


@pytest.fixture
def mock_orderbook():
    """Mock orderbook data for testing."""
    return {
        'bids': [
            [100.0, 10.0],   # [price, size]
            [99.5, 15.0],
            [99.0, 20.0],
            [98.5, 25.0],
            [98.0, 30.0]
        ],
        'asks': [
            [100.5, 12.0],
            [101.0, 18.0],
            [101.5, 25.0],
            [102.0, 35.0],
            [102.5, 40.0]
        ]
    }


@pytest.fixture
def mock_order():
    """Mock order object for testing."""
    class MockOrder:
        def __init__(self, side='buy', price=100.0, size_usd=100.0):
            self.side = side
            self.price = price
            self.size_usd = size_usd

    return MockOrder()


@pytest.fixture
async def mock_drift_client(test_config):
    """Mock Drift client for testing."""
    from ultimate_hedge_bot.core.safe_drift_client import SafeDriftClient

    client = SafeDriftClient(test_config)
    # Initialize with mock fallback
    success = await client.safe_initialize()
    assert success
    yield client
    await client.close()


@pytest.fixture
async def mock_rpc_manager(test_config):
    """Mock RPC manager for testing."""
    from ultimate_hedge_bot.infrastructure.safe_rpc_manager import SafeRPCManager

    manager = SafeRPCManager(test_config)
    yield manager
    await manager.stop_health_monitoring()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )


def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on their location."""
    for item in items:
        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark performance tests
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)

        # Mark slow tests
        if "slow" in item.keywords:
            item.add_marker(pytest.mark.slow)

