"""
Pytest configuration and shared fixtures for drift-swift testing.

This module provides common test fixtures, mocks, and utilities
used across all bot unit tests and end-to-end tests.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock

import pytest
import yaml

# Test configuration templates
TEST_CONFIGS = {
    "drift_client": {
        "drift": {
            "cluster": "testnet",
            "keypair_path": ".test_wallet.json",
            "market_index": 0,
            "sub_account_id": 0,
            "commitment": "confirmed"
        },
        "swift": {
            "base_url": "http://localhost:8080",
            "api_key": "test_api_key",
            "timeout": 30
        }
    },

    "jit_bot": {
        "bot": {
            "symbol": "SOL-PERP",
            "max_inventory_usd": 10000,
            "max_position_abs": 50,
            "tick_size": 0.01,
            "min_spread_bps": 5,
            "max_spread_bps": 50,
            "inventory_skew_pct": 0.1,
            "order_refresh_secs": 30,
            "position_limit_pct": 0.8
        },
        "risk": {
            "max_drawdown_pct": 0.05,
            "max_daily_loss_usd": 1000,
            "circuit_breaker_pct": 0.02
        },
        "logging": {
            "level": "INFO",
            "file": "jit_bot_test.log"
        }
    },

    "hedge_bot": {
        "hedge": {
            "max_inventory_usd": 5000,
            "max_position_abs": 25,
            "tick_size": 0.01,
            "hedge_threshold_usd": 1000,
            "hedge_ratio": 0.5,
            "sleep_interval_secs": 10
        },
        "routing": {
            "primary": "drift",
            "fallback": "swift",
            "ioc_timeout_ms": 5000
        },
        "risk": {
            "max_drawdown_pct": 0.03,
            "max_daily_loss_usd": 500,
            "circuit_breaker_pct": 0.01
        }
    },

    "trend_bot": {
        "trend": {
            "symbol": "SOL-PERP",
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "price_history_len": 100,
            "min_signal_strength": 0.001,
            "position_size_usd": 1000,
            "sleep_interval_secs": 60
        },
        "filters": {
            "atr_period": 14,
            "atr_threshold": 1.5,
            "adx_period": 14,
            "adx_threshold": 25
        },
        "risk": {
            "max_drawdown_pct": 0.04,
            "max_daily_loss_usd": 750,
            "circuit_breaker_pct": 0.015
        }
    }
}


class MockDriftClient:
    """Mock Drift client for testing."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connected = False
        self.orders = []
        self.positions = {"SOL-PERP": {"size": 0.0, "entry_price": 0.0, "unrealized_pnl": 0.0}}

    async def connect(self):
        """Mock connect method."""
        self.connected = True
        return True

    async def disconnect(self):
        """Mock disconnect method."""
        self.connected = False

    async def get_orderbook(self, symbol: str) -> Dict[str, Any]:
        """Mock get orderbook."""
        return {
            "symbol": symbol,
            "bids": [[100.0, 10.0], [99.9, 15.0], [99.8, 20.0]],
            "asks": [[100.2, 10.0], [100.3, 15.0], [100.4, 20.0]],
            "timestamp": 1234567890
        }

    async def place_order(self, order) -> str:
        """Mock place order."""
        tx_sig = f"mock_tx_{len(self.orders)}"
        self.orders.append({
            "id": tx_sig,
            "symbol": getattr(order, 'symbol', 'SOL-PERP'),
            "side": getattr(order, 'side', 'buy'),
            "qty": getattr(order, 'qty', 1.0),
            "price": getattr(order, 'price', 100.0),
            "timestamp": 1234567890
        })
        return tx_sig

    async def cancel_order(self, order_id: str) -> bool:
        """Mock cancel order."""
        return True

    async def get_positions(self) -> Dict[str, Any]:
        """Mock get positions."""
        return self.positions

    def get_position_value_usd(self, symbol: str) -> float:
        """Mock get position value."""
        pos = self.positions.get(symbol, {})
        return pos.get("size", 0.0) * pos.get("entry_price", 0.0)


class MockRiskManager:
    """Mock Risk Manager for testing."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state = Mock()
        self.state.drawdown_pct = 0.0
        self.state.daily_loss_usd = 0.0
        self.state.can_trade = True

    def assess_risk(self, positions: Dict[str, Any], orders: list) -> Mock:
        """Mock risk assessment."""
        return self.state

    def update_pnl(self, pnl: float):
        """Mock PNL update."""
        pass


class MockOrderManager:
    """Mock Order Manager for testing."""

    def __init__(self):
        self.orders = []
        self.active_orders = {}

    def add_order(self, order):
        """Add order to tracking."""
        order_id = f"order_{len(self.orders)}"
        self.orders.append({
            "id": order_id,
            "symbol": getattr(order, 'symbol', 'SOL-PERP'),
            "side": getattr(order, 'side', 'buy'),
            "qty": getattr(order, 'qty', 1.0),
            "price": getattr(order, 'price', 100.0),
            "status": "placed",
            "timestamp": 1234567890
        })
        self.active_orders[order_id] = self.orders[-1]
        return order_id

    def get_active_orders(self, symbol: Optional[str] = None) -> list:
        """Get active orders."""
        if symbol:
            return [o for o in self.active_orders.values() if o["symbol"] == symbol]
        return list(self.active_orders.values())

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order."""
        if order_id in self.active_orders:
            self.active_orders[order_id]["status"] = "cancelled"
            return True
        return False


class MockPositionTracker:
    """Mock Position Tracker for testing."""

    def __init__(self):
        self.positions = {}
        self.net_exposure_usd = 0.0

    def update_position(self, symbol: str, size: float, price: float):
        """Update position."""
        self.positions[symbol] = {
            "size": size,
            "avg_price": price,
            "current_price": price,
            "unrealized_pnl": 0.0
        }
        self._update_net_exposure()

    def get_net_exposure_usd(self) -> float:
        """Get net exposure in USD."""
        return self.net_exposure_usd

    def _update_net_exposure(self):
        """Update net exposure calculation."""
        total = 0.0
        for pos in self.positions.values():
            total += pos["size"] * pos["avg_price"]
        self.net_exposure_usd = total


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config():
    """Provide test configuration templates."""
    return TEST_CONFIGS


@pytest.fixture
def mock_drift_client(test_config):
    """Create a mock Drift client."""
    return MockDriftClient(test_config["drift_client"])


@pytest.fixture
def mock_risk_manager(test_config):
    """Create a mock risk manager."""
    return MockRiskManager(test_config["jit_bot"]["risk"])


@pytest.fixture
def mock_order_manager():
    """Create a mock order manager."""
    return MockOrderManager()


@pytest.fixture
def mock_position_tracker():
    """Create a mock position tracker."""
    return MockPositionTracker()


@pytest.fixture
def sample_orderbook():
    """Sample orderbook data for testing."""
    return {
        "symbol": "SOL-PERP",
        "bids": [
            [100.0, 10.0],
            [99.9, 15.0],
            [99.8, 20.0],
            [99.7, 25.0],
            [99.6, 30.0]
        ],
        "asks": [
            [100.2, 10.0],
            [100.3, 15.0],
            [100.4, 20.0],
            [100.5, 25.0],
            [100.6, 30.0]
        ],
        "timestamp": 1234567890
    }


@pytest.fixture
def sample_positions():
    """Sample position data for testing."""
    return {
        "SOL-PERP": {
            "size": 10.0,
            "avg_price": 100.0,
            "current_price": 105.0,
            "unrealized_pnl": 50.0
        }
    }


def create_test_config_file(config_data: Dict[str, Any], temp_dir: Path) -> str:
    """Create a temporary config file for testing."""
    config_path = temp_dir / "test_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config_data, f)
    return str(config_path)


@pytest.fixture
def jit_config_file(temp_dir, test_config):
    """Create JIT bot config file."""
    return create_test_config_file(test_config["jit_bot"], temp_dir)


@pytest.fixture
def hedge_config_file(temp_dir, test_config):
    """Create hedge bot config file."""
    return create_test_config_file(test_config["hedge_bot"], temp_dir)


@pytest.fixture
def trend_config_file(temp_dir, test_config):
    """Create trend bot config file."""
    return create_test_config_file(test_config["trend_bot"], temp_dir)

