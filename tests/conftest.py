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
    },

    "swift_mm_bot": {
        "env": "devnet",
        "rpc_url": "https://test-rpc.com",
        "sidecar_url": "http://localhost:8787",
        "swift_websocket_url": "wss://test-swift.com/ws",
        "wallet_file": ".test_wallet.json",
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
        "toxicity_guard": True
    },

    "capital_allocator": {
        "max_leverage": 5.0,
        "leverage_buffer": 0.8,
        "min_collateral_buffer": 50.0,
        "min_trade_usd": 25.0
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


@pytest.fixture
def swift_mm_config_file(temp_dir, test_config):
    """Create Swift MM bot config file."""
    return create_test_config_file(test_config["swift_mm_bot"], temp_dir)


@pytest.fixture
def swift_mm_config(test_config):
    """Get Swift MM bot configuration."""
    return test_config["swift_mm_bot"]


@pytest.fixture
def test_wallet_file():
    """Create a temporary wallet file for testing."""
    import tempfile
    import json
    
    wallet_data = [1, 2, 3, 4, 5] * 32  # 160 bytes for Solana keypair
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(wallet_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    import os
    try:
        os.unlink(temp_path)
    except OSError:
        pass


@pytest.fixture
def mock_swift_components():
    """Mock Swift-related components for testing."""
    from unittest.mock import Mock, AsyncMock
    
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


class MockCapitalAllocation:
    """Mock CapitalAllocation for testing."""

    def __init__(self, bot_id="test_bot", max_trade_usd=100.0, available_capital_usd=1000.0,
                 max_position_sol=3.0, leverage_factor=5.0, min_trade_sol=0.1, max_trade_sol=2.0,
                 free_collateral_usd=1000.0, total_collateral_usd=2000.0, current_position_sol=0.0):
        self.bot_id = bot_id
        self.max_trade_usd = max_trade_usd
        self.available_capital_usd = available_capital_usd
        self.max_position_sol = max_position_sol
        self.leverage_factor = leverage_factor
        self.min_trade_sol = min_trade_sol
        self.max_trade_sol = max_trade_sol
        self.free_collateral_usd = free_collateral_usd
        self.total_collateral_usd = total_collateral_usd
        self.current_position_sol = current_position_sol


class MockCapitalAllocator:
    """Mock capital allocator for testing the capital allocation architecture."""

    def __init__(self):
        self.allocations = {
            "shotgun_mm": {
                "max_trade_usd": 100.0,
                "available_capital_usd": 400.0,
                "risk_limit_usd": 50.0,
                "max_position_usd": 500.0,
            },
            "sniper_mm": {
                "max_trade_usd": 200.0,
                "available_capital_usd": 800.0,
                "risk_limit_usd": 100.0,
                "max_position_usd": 1000.0,
            },
            "hedge": {
                "max_trade_usd": 500.0,
                "available_capital_usd": 2000.0,
                "risk_limit_usd": 250.0,
                "max_position_usd": 2500.0,
            },
            "trend": {
                "max_trade_usd": 300.0,
                "available_capital_usd": 1200.0,
                "risk_limit_usd": 150.0,
                "max_position_usd": 1500.0,
            },
            "jit_mm": {
                "max_trade_usd": 75.0,
                "available_capital_usd": 300.0,
                "risk_limit_usd": 37.5,
                "max_position_usd": 375.0,
            }
        }

    async def get_capital_allocation(self, bot_id: str, drift_user):
        """Get mock capital allocation for testing."""
        from libs.orchestration.capital_allocator import CapitalAllocation

        if bot_id not in self.allocations:
            return CapitalAllocation(
                bot_id=bot_id,
                max_trade_usd=0.0,
                available_capital_usd=0.0,
                current_position_usd=0.0,
                risk_limit_usd=0.0,
                can_trade=False,
                reason=f"Unknown bot type: {bot_id}"
            )

        config = self.allocations[bot_id]
        # Mock current position for testing
        current_position_usd = getattr(drift_user, 'current_position_usd', 0.0)
        max_position_usd = config["max_position_usd"]
        available_capital_usd = max(max_position_usd - abs(current_position_usd), 0.0)

        # Determine if trading is allowed
        risk_limit_usd = config["risk_limit_usd"]
        position_utilization = abs(current_position_usd) / max_position_usd

        if position_utilization > 0.95:
            can_trade = False
            reason = f"Position utilization too high: {position_utilization:.1%}"
        elif available_capital_usd < risk_limit_usd:
            can_trade = False
            reason = f"Insufficient capital: {available_capital_usd:.2f} < {risk_limit_usd:.2f}"
        else:
            can_trade = True
            reason = None

        return CapitalAllocation(
            bot_id=bot_id,
            max_trade_usd=config["max_trade_usd"],
            available_capital_usd=available_capital_usd,
            current_position_usd=current_position_usd,
            risk_limit_usd=risk_limit_usd,
            can_trade=can_trade,
            reason=reason
        )

    def get_bot_config(self, bot_id: str):
        """Get mock bot configuration."""
        configs = {
            "shotgun_mm": {
                "strategy": "high_frequency",
                "max_orders_per_side": 1,
                "position_tolerance": 0.1,
            },
            "sniper_mm": {
                "strategy": "precision",
                "max_orders_per_side": 1,
                "position_tolerance": 0.05,
            },
            "hedge": {
                "strategy": "hedging",
                "max_orders_per_side": 3,
                "position_tolerance": 0.2,
            },
            "trend": {
                "strategy": "momentum",
                "max_orders_per_side": 2,
                "position_tolerance": 0.15,
            },
            "jit_mm": {
                "strategy": "just_in_time",
                "max_orders_per_side": 1,
                "position_tolerance": 0.08,
            }
        }
        return configs.get(bot_id, {})


class MockCapitalAllocator:
    """Mock CapitalAllocator for testing."""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.stats = {
            "total_allocations": 0,
            "successful_allocations": 0,
            "failed_allocations": 0,
            "avg_processing_time_ms": 1.5,
            "allocations_by_bot": {}
        }
        self._should_fail = False
    
    def set_should_fail(self, fail: bool):
        """Set whether allocations should fail (for testing)."""
        self._should_fail = fail
    
    async def get_capital_allocation(self, bot_id: str, drift_user) -> Optional[MockCapitalAllocation]:
        """Mock get capital allocation."""
        self.stats["total_allocations"] += 1
        
        if self._should_fail:
            self.stats["failed_allocations"] += 1
            return None
        
        # Default allocation based on bot type
        if "shotgun" in bot_id.lower():
            allocation = MockCapitalAllocation(
                bot_id=bot_id,
                max_trade_usd=100.0,
                max_position_sol=3.0
            )
        elif "sniper" in bot_id.lower():
            allocation = MockCapitalAllocation(
                bot_id=bot_id,
                max_trade_usd=400.0,
                max_position_sol=5.0
            )
        elif "hedge" in bot_id.lower():
            allocation = MockCapitalAllocation(
                bot_id=bot_id,
                max_trade_usd=500.0,
                max_position_sol=10.0
            )
        elif "trend" in bot_id.lower():
            allocation = MockCapitalAllocation(
                bot_id=bot_id,
                max_trade_usd=600.0,
                max_position_sol=15.0
            )
        else:
            allocation = MockCapitalAllocation(
                bot_id=bot_id,
                max_trade_usd=250.0,
                max_position_sol=4.0
            )
        
        self.stats["successful_allocations"] += 1
        if bot_id not in self.stats["allocations_by_bot"]:
            self.stats["allocations_by_bot"][bot_id] = 0
        self.stats["allocations_by_bot"][bot_id] += 1
        
        return allocation
    
    def can_trade(self, allocation: MockCapitalAllocation, requested_usd: float) -> bool:
        """Mock can trade validation."""
        return (
            allocation.free_collateral_usd > 50.0 and
            requested_usd <= allocation.max_trade_usd and
            requested_usd >= 25.0
        )
    
    def get_performance_stats(self) -> Dict:
        """Mock get performance stats."""
        success_rate = 0.0
        if self.stats["total_allocations"] > 0:
            success_rate = (self.stats["successful_allocations"] / self.stats["total_allocations"]) * 100
        
        return {
            **self.stats,
            "success_rate_percent": round(success_rate, 2)
        }


class MockDriftUserForCapital:
    """Mock DriftUser for capital allocation testing."""
    
    def __init__(self, total_collateral=2000000, free_collateral=1000000, positions=None):
        self.total_collateral = total_collateral
        self.free_collateral = free_collateral
        self.positions = positions or []
    
    def get_total_collateral(self):
        return self.total_collateral
    
    def get_free_collateral(self):
        return self.free_collateral
    
    def get_perp_positions(self):
        return self.positions


@pytest.fixture
def capital_allocator_config(test_config):
    """Capital allocator configuration for testing."""
    return test_config["capital_allocator"]


@pytest.fixture
def mock_capital_allocator(capital_allocator_config):
    """Create a mock capital allocator."""
    return MockCapitalAllocator(capital_allocator_config)


@pytest.fixture
def mock_drift_user_for_capital():
    """Create a mock drift user for capital allocation testing."""
    return MockDriftUserForCapital(
        total_collateral=2000000,  # $2000 (scaled by 1e6)
        free_collateral=1000000,   # $1000 (scaled by 1e6)
        positions=[]
    )


@pytest.fixture
def mock_capital_allocation():
    """Create a mock capital allocation."""
    return MockCapitalAllocation(
        bot_id="test_bot",
        max_trade_usd=100.0,
        available_capital_usd=1000.0,
        max_position_sol=3.0,
        leverage_factor=5.0,
        min_trade_sol=0.1,
        max_trade_sol=2.0,
        free_collateral_usd=1000.0,
        total_collateral_usd=2000.0,
        current_position_sol=0.0
    )


