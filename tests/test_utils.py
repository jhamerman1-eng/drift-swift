#!/usr/bin/env python3
"""
Test Utilities and Helpers for Swift MM Bot

This module provides common utilities, fixtures, and helpers used across
all test suites for the Swift Market Making Bot.
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from dataclasses import dataclass

import pytest
import yaml

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from run_swift_mm_complete import (
    CompleteSwiftMMBot, JITConfig, InventoryManager, OBICalculator,
    SpreadManager, PnLTracker, OrderInfo, PositionEntry, TradeRecord
)


@dataclass
class MockOrderbook:
    """Mock orderbook for testing."""
    symbol: str = "SOL-PERP"
    bids: List[List[float]] = None
    asks: List[List[float]] = None
    timestamp: int = None

    def __post_init__(self):
        if self.bids is None:
            self.bids = [[100.0, 10.0], [99.9, 15.0], [99.8, 20.0]]
        if self.asks is None:
            self.asks = [[100.2, 10.0], [100.3, 15.0], [100.4, 20.0]]
        if self.timestamp is None:
            self.timestamp = int(time.time())


@dataclass
class MockPosition:
    """Mock position for testing."""
    symbol: str = "SOL-PERP"
    size: float = 10.0
    avg_price: float = 100.0
    current_price: float = 105.0
    unrealized_pnl: float = 50.0


class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    def create_test_wallet(temp_dir: Path) -> str:
        """Create a test wallet file."""
        wallet_data = [1, 2, 3, 4, 5] * 32  # 160 bytes for Solana keypair

        wallet_path = temp_dir / "test_wallet.json"
        with open(wallet_path, 'w') as f:
            json.dump(wallet_data, f)

        return str(wallet_path)

    @staticmethod
    def create_test_config(temp_dir: Path, **overrides) -> Dict[str, Any]:
        """Create a test configuration file."""
        base_config = {
            "env": "devnet",
            "rpc_url": "https://test-rpc.com",
            "sidecar_url": "http://localhost:8787",
            "swift_websocket_url": "wss://test-swift.com/ws",
            "wallet_file": TestDataFactory.create_test_wallet(temp_dir),
            "order_size": 0.01,
            "max_orders_per_side": 1,
            "price_tolerance": 0.01,
            "spread_bps": 8,
            "symbol": "SOL-PERP",
            "leverage": 10,
            "max_position_abs": 120.0,
            "inventory_target": 0.0,
            "spread_bps_min": 4.0,
            "spread_bps_max": 25.0,
            "post_only": True,
            "obi_microprice": True,
            "cancel_replace_enabled": True,
            "cancel_replace_interval_ms": 1000,
            "toxicity_guard": True,
            "max_order_size_usd": 1000.0,
            "max_daily_loss_usd": 5000.0
        }

        base_config.update(overrides)
        return base_config

    @staticmethod
    def create_test_orderbook(mid_price: float = 100.0, spread: float = 1.0, depth: int = 5) -> MockOrderbook:
        """Create a test orderbook."""
        bids = []
        asks = []

        for i in range(depth):
            bids.append([mid_price - spread * (i + 1) / depth, 10.0 + i])
            asks.append([mid_price + spread * (i + 1) / depth, 10.0 + i])

        return MockOrderbook(
            symbol="SOL-PERP",
            bids=bids,
            asks=asks,
            timestamp=int(time.time())
        )

    @staticmethod
    def create_test_positions() -> Dict[str, MockPosition]:
        """Create test positions."""
        return {
            "SOL-PERP": MockPosition(
                symbol="SOL-PERP",
                size=10.0,
                avg_price=100.0,
                current_price=105.0,
                unrealized_pnl=50.0
            )
        }


class MockFactory:
    """Factory for creating mocks."""

    @staticmethod
    def create_mock_drift_client():
        """Create a mock DriftClient."""
        client = Mock()
        client.add_user = AsyncMock()
        client.subscribe = AsyncMock()
        client.get_user = Mock()
        client.get_l2_orderbook = Mock(return_value={
            "bids": [[100.0, 1.0], [99.9, 2.0]],
            "asks": [[100.1, 1.0], [100.2, 2.0]]
        })
        client.get_oracle_price_data_for_perp_market = Mock()
        client.decode_signed_msg_order_params_message = Mock()
        client.connection = Mock()
        client.connection.get_slot = AsyncMock(return_value=Mock(value=12345))

        return client

    @staticmethod
    def create_mock_swift_components():
        """Create mock Swift components."""
        mock_sidecar = Mock()
        mock_sidecar.health = AsyncMock(return_value={"status": "ok"})
        mock_sidecar.place_order = Mock(return_value={"ok": True, "id": "test_order_123"})
        mock_sidecar.cancel_order = AsyncMock(return_value={"ok": True})
        mock_sidecar.close = Mock()

        mock_envelope_creator = Mock()
        mock_envelope_creator.create_order_envelope = Mock(return_value={"order": "test_envelope"})
        mock_envelope_creator.create_cancel_envelope = Mock(return_value={"cancel": "test_cancel_envelope"})

        mock_websocket_receiver = Mock()
        mock_websocket_receiver.start = AsyncMock()
        mock_websocket_receiver.stop = AsyncMock()

        mock_order_processor = Mock()
        mock_order_processor.process_order = AsyncMock(return_value={"status": "success", "message": "Order processed"})
        mock_order_processor.get_stats = Mock(return_value={"processed": 0, "errors": 0})

        return {
            "sidecar": mock_sidecar,
            "envelope_creator": mock_envelope_creator,
            "websocket_receiver": mock_websocket_receiver,
            "order_processor": mock_order_processor
        }

    @staticmethod
    def create_mock_risk_manager():
        """Create a mock risk manager."""
        risk_manager = Mock()
        risk_manager.assess_risk = Mock(return_value=Mock(
            drawdown_pct=0.0,
            daily_loss_usd=0.0,
            can_trade=True
        ))
        risk_manager.update_pnl = Mock()
        return risk_manager

    @staticmethod
    def create_mock_order_manager():
        """Create a mock order manager."""
        order_manager = Mock()
        order_manager.add_order = Mock(return_value="order_123")
        order_manager.get_active_orders = Mock(return_value=[])
        order_manager.cancel_order = Mock(return_value=True)
        return order_manager


class AsyncTestHelper:
    """Helper for async testing."""

    @staticmethod
    async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
        """Wait for a condition to be true."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if condition_func():
                return True
            await asyncio.sleep(interval)

        return False

    @staticmethod
    async def run_with_timeout(coro, timeout: float = 5.0):
        """Run a coroutine with a timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            pytest.fail(f"Coroutine timed out after {timeout} seconds")


class EnvironmentHelper:
    """Helper for environment variable testing."""

    @staticmethod
    def set_env_vars(env_vars: Dict[str, str]):
        """Set environment variables for testing."""
        return patch.dict(os.environ, env_vars)

    @staticmethod
    def clear_env_vars():
        """Clear all environment variables."""
        return patch.dict(os.environ, {}, clear=True)

    @staticmethod
    def mock_env_config():
        """Create mock environment configuration."""
        return {
            'DRIFT_ENV': 'mainnet',
            'RPC_URL': 'https://api.mainnet.solana.com',
            'SWIFT_SIDECAR_URL': 'https://api.drift.trade',
            'SWIFT_WEBSOCKET_URL': 'wss://api.drift.trade/ws',
            'SWIFT_API_KEY': 'prod_key_123',
            'ORDER_SIZE': '0.1',
            'MAX_POSITION_ABS': '200',
            'SPREAD_BPS': '10',
            'LEVERAGE': '5',
            'MAX_DAILY_LOSS_USD': '10000'
        }


class ConfigValidator:
    """Helper for validating configuration."""

    @staticmethod
    def validate_bot_config(config: Dict[str, Any]) -> List[str]:
        """Validate bot configuration."""
        errors = []

        # Required string fields
        required_strings = ['env', 'rpc_url', 'wallet_file']
        for field in required_strings:
            if field not in config:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(config[field], str):
                errors.append(f"Field {field} must be a string")

        # Required numeric fields
        required_numbers = ['order_size', 'max_orders_per_side', 'price_tolerance']
        for field in required_numbers:
            if field not in config:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(config[field], (int, float)):
                errors.append(f"Field {field} must be a number")

        # Validate ranges
        if 'order_size' in config and config['order_size'] <= 0:
            errors.append("order_size must be positive")

        if 'max_orders_per_side' in config and config['max_orders_per_side'] <= 0:
            errors.append("max_orders_per_side must be positive")

        if 'leverage' in config and config['leverage'] <= 0:
            errors.append("leverage must be positive")

        return errors

    @staticmethod
    def validate_env_vars(env_vars: Dict[str, str]) -> List[str]:
        """Validate environment variables."""
        errors = []

        # Check for required environment variables
        required_env_vars = ['DRIFT_ENV', 'RPC_URL']
        for var in required_env_vars:
            if var not in env_vars:
                errors.append(f"Missing required environment variable: {var}")

        # Validate URLs
        url_vars = ['RPC_URL', 'SWIFT_SIDECAR_URL', 'SWIFT_WEBSOCKET_URL']
        for var in url_vars:
            if var in env_vars:
                value = env_vars[var]
                if not (value.startswith('http') or value.startswith('wss')):
                    errors.append(f"Invalid URL format for {var}: {value}")

        # Validate numeric conversions
        numeric_vars = ['ORDER_SIZE', 'MAX_POSITION_ABS', 'SPREAD_BPS', 'LEVERAGE', 'MAX_DAILY_LOSS_USD']
        for var in numeric_vars:
            if var in env_vars:
                try:
                    float(env_vars[var])
                except ValueError:
                    errors.append(f"Invalid numeric value for {var}: {env_vars[var]}")

        return errors


class PerformanceMonitor:
    """Helper for monitoring test performance."""

    def __init__(self):
        self.start_time = None
        self.measurements = []

    def start(self):
        """Start performance monitoring."""
        self.start_time = time.time()

    def stop(self) -> float:
        """Stop performance monitoring and return duration."""
        if self.start_time is None:
            return 0.0

        duration = time.time() - self.start_time
        self.measurements.append(duration)
        self.start_time = None
        return duration

    def get_average_duration(self) -> float:
        """Get average duration of measurements."""
        if not self.measurements:
            return 0.0
        return sum(self.measurements) / len(self.measurements)

    def get_total_duration(self) -> float:
        """Get total duration of all measurements."""
        return sum(self.measurements)

    def reset(self):
        """Reset performance measurements."""
        self.measurements = []
        self.start_time = None


# Common pytest fixtures
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_wallet(temp_dir):
    """Create a test wallet file."""
    return TestDataFactory.create_test_wallet(temp_dir)


@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration."""
    return TestDataFactory.create_test_config(temp_dir)


@pytest.fixture
def mock_orderbook():
    """Create a mock orderbook."""
    return TestDataFactory.create_test_orderbook()


@pytest.fixture
def mock_positions():
    """Create mock positions."""
    return TestDataFactory.create_test_positions()


@pytest.fixture
def mock_drift_client():
    """Create a mock DriftClient."""
    return MockFactory.create_mock_drift_client()


@pytest.fixture
def mock_swift_components():
    """Create mock Swift components."""
    return MockFactory.create_mock_swift_components()


@pytest.fixture
def mock_risk_manager():
    """Create a mock risk manager."""
    return MockFactory.create_mock_risk_manager()


@pytest.fixture
def mock_order_manager():
    """Create a mock order manager."""
    return MockFactory.create_mock_order_manager()


@pytest.fixture
def env_helper():
    """Create an environment helper."""
    return EnvironmentHelper()


@pytest.fixture
def config_validator():
    """Create a config validator."""
    return ConfigValidator()


@pytest.fixture
def perf_monitor():
    """Create a performance monitor."""
    return PerformanceMonitor()


@pytest.fixture
def async_helper():
    """Create an async test helper."""
    return AsyncTestHelper()


# Common test utilities
def assert_config_valid(config: Dict[str, Any]):
    """Assert that configuration is valid."""
    validator = ConfigValidator()
    errors = validator.validate_bot_config(config)
    assert not errors, f"Configuration validation failed: {errors}"


def assert_env_vars_valid(env_vars: Dict[str, str]):
    """Assert that environment variables are valid."""
    validator = ConfigValidator()
    errors = validator.validate_env_vars(env_vars)
    assert not errors, f"Environment variable validation failed: {errors}"


def assert_orderbook_valid(orderbook):
    """Assert that orderbook is valid."""
    assert hasattr(orderbook, 'bids'), "Orderbook must have bids"
    assert hasattr(orderbook, 'asks'), "Orderbook must have asks"
    assert len(orderbook.bids) > 0, "Orderbook must have bid orders"
    assert len(orderbook.asks) > 0, "Orderbook must have ask orders"

    # Check that bids are in descending order and asks in ascending order
    for i in range(1, len(orderbook.bids)):
        assert orderbook.bids[i][0] < orderbook.bids[i-1][0], "Bids must be in descending order"

    for i in range(1, len(orderbook.asks)):
        assert orderbook.asks[i][0] > orderbook.asks[i-1][0], "Asks must be in ascending order"


def assert_positions_valid(positions: Dict[str, Any]):
    """Assert that positions are valid."""
    for symbol, position in positions.items():
        assert isinstance(position.size, (int, float)), f"Position size must be numeric for {symbol}"
        assert isinstance(position.avg_price, (int, float)), f"Average price must be numeric for {symbol}"
        assert position.avg_price > 0, f"Average price must be positive for {symbol}"


# Test data constants
TEST_SYMBOLS = ["SOL-PERP", "BTC-PERP", "ETH-PERP"]
TEST_ENVIRONMENTS = ["devnet", "mainnet", "testnet"]
TEST_ORDER_SIZES = [0.01, 0.05, 0.1, 0.5, 1.0]
TEST_LEVERAGES = [1, 5, 10, 20, 50]
TEST_SPREADS = [0.1, 1.0, 5.0, 10.0, 25.0]

if __name__ == "__main__":
    # Test the utilities
    print("Testing test utilities...")

    # Test data factory
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        wallet_path = TestDataFactory.create_test_wallet(temp_path)
        config = TestDataFactory.create_test_config(temp_path)
        orderbook = TestDataFactory.create_test_orderbook()

        print(f"✅ Created test wallet: {wallet_path}")
        print(f"✅ Created test config: {config['env']}")
        print(f"✅ Created test orderbook: {len(orderbook.bids)} bids, {len(orderbook.asks)} asks")

    # Test config validation
    validator = ConfigValidator()
    test_config = {
        "env": "devnet",
        "rpc_url": "https://test-rpc.com",
        "wallet_file": "/tmp/test_wallet.json",
        "order_size": 0.01,
        "max_orders_per_side": 1,
        "price_tolerance": 0.01
    }

    errors = validator.validate_bot_config(test_config)
    if errors:
        print(f"❌ Config validation errors: {errors}")
    else:
        print("✅ Config validation passed")

    print("✅ All test utilities working correctly")
