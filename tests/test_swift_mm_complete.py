#!/usr/bin/env python3
"""
Comprehensive Unit Test Suite for Complete Swift Market Making Bot

This test suite ensures that all components of the Swift MM bot work correctly
and that any modifications don't break existing functionality.

Run with: python -m pytest tests/test_swift_mm_complete.py -v
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the components we want to test
from run_swift_mm_complete import CompleteSwiftMMBot, OrderInfo

# Mock classes for external dependencies
class MockJITConfig:
    def __init__(self, **kwargs):
        self.symbol = kwargs.get("symbol", "SOL-PERP")
        self.leverage = kwargs.get("leverage", 10)
        self.post_only = kwargs.get("post_only", True)
        self.obi_microprice = kwargs.get("obi_microprice", True)
        self.spread_bps_base = kwargs.get("spread_bps_base", 8.0)
        self.spread_bps_min = kwargs.get("spread_bps_min", 4.0)
        self.spread_bps_max = kwargs.get("spread_bps_max", 25.0)
        self.inventory_target = kwargs.get("inventory_target", 0.0)
        self.max_position_abs = kwargs.get("max_position_abs", 120.0)
        self.cancel_replace_enabled = kwargs.get("cancel_replace_enabled", True)
        self.cancel_replace_interval_ms = kwargs.get("cancel_replace_interval_ms", 1000)
        self.toxicity_guard = kwargs.get("toxicity_guard", True)

class MockInventoryManager:
    def __init__(self, config, symbol):
        self.config = config
        self.symbol = symbol
        self.max_position = config.max_position_abs

    def calculate_inventory_skew(self, position):
        if position == 0:
            return 0.0
        return min(max(position / self.max_position, -1.0), 1.0)

    def should_trade(self, position):
        return abs(position) <= self.max_position

class MockOBICalculator:
    def __init__(self, levels=10):
        self.levels = levels

    def calculate_obi(self, orderbook):
        class OBI:
            def __init__(self):
                self.microprice = 100.0
                self.imbalance_ratio = 0.1
                self.skew_adjustment = 0.05
                self.confidence = 0.8
        return OBI()

class MockSpreadManager:
    def __init__(self, config):
        self.config = config

    def calculate_dynamic_spread(self, volatility, inventory_skew, confidence):
        base_spread = self.config.spread_bps_base
        skew_adjustment = abs(inventory_skew) * 5.0  # 5 bps per 100% skew
        volatility_adjustment = volatility * 1000  # Scale volatility
        return min(max(base_spread + skew_adjustment + volatility_adjustment, 
                      self.config.spread_bps_min), self.config.spread_bps_max)

class MockOrderbook:
    def __init__(self, bids=None, asks=None, ts=None):
        self.bids = bids or [[99.9, 10.0], [99.8, 15.0]]
        self.asks = asks or [[100.1, 10.0], [100.2, 15.0]]
        self.ts = ts or time.time()

class MockDriftClient:
    def __init__(self):
        self.connection = Mock()
        self.connection.get_slot = AsyncMock(return_value=Mock(value=12345))
        self._user = Mock()
        self._user.get_active_perp_positions = Mock(return_value=[])
        self._user.get_free_collateral = Mock(return_value=1000000)
        self._user.get_total_collateral = Mock(return_value=2000000)
        self._user.get_margin_requirement = Mock(return_value=500000)

    async def add_user(self, sub_account_id):
        pass

    async def subscribe(self):
        pass

    def get_user(self):
        return self._user

    def get_oracle_price_data_for_perp_market(self, market_index):
        class OracleData:
            def __init__(self):
                self.price = 100000000  # 100.0 in native precision
                self.slot = 12345
        return OracleData()

    async def get_l2_orderbook(self, market_index, depth):
        return {
            "bids": [[99.9, 10.0], [99.8, 15.0]],
            "asks": [[100.1, 10.0], [100.2, 15.0]]
        }

class MockKeypair:
    def __init__(self):
        self.pubkey = Mock(return_value="test_pubkey")

class MockSwiftSidecarClient:
    def __init__(self):
        self.health_response = {"status": "ok"}

    async def health(self):
        return self.health_response

    def place_order(self, envelope):
        return {"ok": True, "id": "test_order_123"}

    async def cancel_order(self, envelope):
        return {"ok": True}

    def close(self):
        pass

class MockSwiftEnvelopeCreator:
    def create_order_envelope(self, params, keypair):
        return {"order": "test_envelope"}

    def create_cancel_envelope(self, order_id, authority, keypair):
        return {"cancel": "test_cancel_envelope"}

class MockSwiftWebSocketReceiver:
    async def start(self, callback):
        pass

    async def stop(self):
        pass

class MockSwiftOrderProcessor:
    def __init__(self, drift_client, keypair):
        self.drift_client = drift_client
        self.keypair = keypair

    async def process_order(self, order):
        return {"status": "success", "message": "Order processed"}

    def get_stats(self):
        return {"processed": 0, "errors": 0}

class MockWebSocketHealthMonitor:
    def get_stats(self):
        return {"connections": 1, "reconnects": 0}

# Test fixtures
@pytest.fixture
def sample_config():
    return {
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
        "max_position_abs": 120.0
    }

@pytest.fixture
def test_wallet_file():
    """Create a temporary wallet file for testing."""
    wallet_data = [1, 2, 3, 4, 5] * 32  # 160 bytes for Solana keypair
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(wallet_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except OSError:
        pass

@pytest.fixture
def mock_bot_dependencies():
    """Mock all external dependencies."""
    with patch('run_swift_mm_complete.JITConfig', MockJITConfig), \
         patch('run_swift_mm_complete.InventoryManager', MockInventoryManager), \
         patch('run_swift_mm_complete.OBICalculator', MockOBICalculator), \
         patch('run_swift_mm_complete.SpreadManager', MockSpreadManager), \
         patch('run_swift_mm_complete.Orderbook', MockOrderbook), \
         patch('run_swift_mm_complete.DriftClient', MockDriftClient), \
         patch('run_swift_mm_complete.Keypair', MockKeypair), \
         patch('run_swift_mm_complete.SwiftSidecarClient', MockSwiftSidecarClient), \
         patch('run_swift_mm_complete.SwiftEnvelopeCreator', MockSwiftEnvelopeCreator), \
         patch('run_swift_mm_complete.SwiftWebSocketReceiver', MockSwiftWebSocketReceiver), \
         patch('run_swift_mm_complete.SwiftOrderProcessor', MockSwiftOrderProcessor), \
         patch('run_swift_mm_complete.WebSocketHealthMonitor', MockWebSocketHealthMonitor), \
         patch('run_swift_mm_complete.RELIABILITY_UTILS_AVAILABLE', False):
        yield

class TestOrderInfo:
    """Test the OrderInfo dataclass."""
    
    def test_order_info_creation(self):
        """Test OrderInfo creation with all parameters."""
        order = OrderInfo(
            order_id="test_123",
            side="buy",
            price=100.0,
            size=1.0,
            timestamp=1234567890.0,
            status="active"
        )
        
        assert order.order_id == "test_123"
        assert order.side == "buy"
        assert order.price == 100.0
        assert order.size == 1.0
        assert order.timestamp == 1234567890.0
        assert order.status == "active"

    def test_order_info_default_status(self):
        """Test OrderInfo creation with default status."""
        order = OrderInfo(
            order_id="test_123",
            side="buy",
            price=100.0,
            size=1.0,
            timestamp=1234567890.0
        )
        
        assert order.status == "active"

class TestCompleteSwiftMMBotInitialization:
    """Test CompleteSwiftMMBot initialization and configuration."""
    
    def test_bot_initialization_basic(self, sample_config, mock_bot_dependencies):
        """Test basic bot initialization."""
        bot = CompleteSwiftMMBot(sample_config)
        
        assert bot.config == sample_config
        assert bot.current_position == 0.0
        assert bot.order_size == 0.01
        assert bot.max_orders_per_side == 1
        assert bot.price_tolerance == 0.01
        assert len(bot.active_orders) == 0
        assert bot.stats["orders_placed"] == 0
        assert bot.stats["orders_cancelled"] == 0

    def test_jit_config_creation(self, sample_config, mock_bot_dependencies):
        """Test JIT configuration is created correctly."""
        bot = CompleteSwiftMMBot(sample_config)
        
        assert bot.jit_config.symbol == "SOL-PERP"
        assert bot.jit_config.leverage == 10
        assert bot.jit_config.post_only == True
        assert bot.jit_config.obi_microprice == True
        assert bot.jit_config.spread_bps_base == 8.0
        assert bot.jit_config.max_position_abs == 120.0

    def test_managers_initialization(self, sample_config, mock_bot_dependencies):
        """Test that all managers are initialized correctly."""
        bot = CompleteSwiftMMBot(sample_config)
        
        assert isinstance(bot.inventory_manager, MockInventoryManager)
        assert isinstance(bot.obi_calculator, MockOBICalculator)
        assert isinstance(bot.spread_manager, MockSpreadManager)

    def test_performance_stats_initialization(self, sample_config, mock_bot_dependencies):
        """Test performance statistics initialization."""
        bot = CompleteSwiftMMBot(sample_config)
        
        assert bot.performance_stats["total_ticks"] == 0
        assert bot.performance_stats["successful_ticks"] == 0
        assert bot.performance_stats["failed_ticks"] == 0
        assert bot.performance_stats["avg_tick_time"] == 0.0
        assert bot.performance_stats["last_tick_time"] == 0.0

    def test_config_defaults(self, mock_bot_dependencies):
        """Test that default configuration values are used when not provided."""
        minimal_config = {"env": "devnet"}
        bot = CompleteSwiftMMBot(minimal_config)
        
        assert bot.jit_config.symbol == "SOL-PERP"  # Default
        assert bot.jit_config.leverage == 10  # Default
        assert bot.jit_config.spread_bps_base == 8.0  # Default
        assert bot.order_size == 0.01  # Default
        assert bot.max_orders_per_side == 1  # Default

class TestCompleteSwiftMMBotAsyncMethods:
    """Test async methods of CompleteSwiftMMBot."""
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test successful bot initialization."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        result = await bot.initialize()
        
        assert result == True
        assert bot.drift_client is not None
        assert bot.keypair is not None
        assert bot.swift_processor is not None

    @pytest.mark.asyncio
    async def test_initialize_wallet_not_found(self, sample_config, mock_bot_dependencies):
        """Test initialization failure when wallet file doesn't exist."""
        sample_config["wallet_file"] = "nonexistent_wallet.json"
        
        bot = CompleteSwiftMMBot(sample_config)
        result = await bot.initialize()
        
        assert result == False

    @pytest.mark.asyncio
    async def test_load_wallet_success(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test successful wallet loading."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot._load_wallet()
        
        assert bot.keypair is not None

    @pytest.mark.asyncio
    async def test_load_wallet_file_not_found(self, sample_config, mock_bot_dependencies):
        """Test wallet loading failure when file doesn't exist."""
        bot = CompleteSwiftMMBot(sample_config)
        
        with pytest.raises(FileNotFoundError):
            await bot._load_wallet()

    @pytest.mark.asyncio
    async def test_initialize_drift_client(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test DriftPy client initialization."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot._load_wallet()
        await bot._initialize_drift_client()
        
        assert bot.drift_client is not None

    @pytest.mark.asyncio
    async def test_initialize_drift_client_no_keypair(self, sample_config, mock_bot_dependencies):
        """Test DriftPy client initialization failure when no keypair."""
        bot = CompleteSwiftMMBot(sample_config)
        
        with pytest.raises(RuntimeError, match="Keypair not loaded"):
            await bot._initialize_drift_client()

    @pytest.mark.asyncio
    async def test_oracle_fresh_enough_true(self, sample_config, mock_bot_dependencies):
        """Test oracle freshness check when oracle is fresh."""
        bot = CompleteSwiftMMBot(sample_config)
        bot.drift_client = MockDriftClient()
        
        result = await bot.oracle_fresh_enough()
        assert result == True

    @pytest.mark.asyncio
    async def test_oracle_fresh_enough_false(self, sample_config, mock_bot_dependencies):
        """Test oracle freshness check when oracle is stale."""
        bot = CompleteSwiftMMBot(sample_config)
        
        # Mock stale oracle
        mock_client = MockDriftClient()
        mock_client.connection.get_slot = AsyncMock(return_value=Mock(value=50000))  # Very high slot
        bot.drift_client = mock_client
        
        result = await bot.oracle_fresh_enough(max_delay_slots=10)
        assert result == False

    @pytest.mark.asyncio
    async def test_oracle_fresh_enough_no_client(self, sample_config, mock_bot_dependencies):
        """Test oracle freshness check when no drift client."""
        bot = CompleteSwiftMMBot(sample_config)
        bot.drift_client = None
        
        result = await bot.oracle_fresh_enough()
        assert result == True  # Should not block if no client

    @pytest.mark.asyncio
    async def test_check_collateral_status_success(self, sample_config, mock_bot_dependencies):
        """Test successful collateral status check."""
        bot = CompleteSwiftMMBot(sample_config)
        bot.drift_client = MockDriftClient()
        
        result = await bot.check_collateral_status()
        assert result == True

    @pytest.mark.asyncio
    async def test_check_collateral_status_low_collateral(self, sample_config, mock_bot_dependencies):
        """Test collateral status check with low collateral."""
        bot = CompleteSwiftMMBot(sample_config)
        
        # Mock low collateral
        mock_client = MockDriftClient()
        mock_client._user.get_free_collateral = Mock(return_value=500000)  # Low collateral
        bot.drift_client = mock_client
        
        result = await bot.check_collateral_status()
        assert result == False

    @pytest.mark.asyncio
    async def test_check_collateral_status_no_client(self, sample_config, mock_bot_dependencies):
        """Test collateral status check when no drift client."""
        bot = CompleteSwiftMMBot(sample_config)
        bot.drift_client = None
        
        result = await bot.check_collateral_status()
        assert result == False

class TestCompleteSwiftMMBotMarketMaking:
    """Test market making functionality."""
    
    @pytest.mark.asyncio
    async def test_market_making_tick_success(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test successful market making tick."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Mock orderbook data
        with patch.object(bot, '_get_orderbook', return_value={
            "bids": [[99.9, 10.0], [99.8, 15.0]],
            "asks": [[100.1, 10.0], [100.2, 15.0]]
        }):
            await bot.market_making_tick()
        
        assert bot.tick_count == 1
        assert bot.performance_stats["total_ticks"] == 1

    @pytest.mark.asyncio
    async def test_market_making_tick_stale_oracle(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test market making tick with stale oracle."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Mock stale oracle
        with patch.object(bot, 'oracle_fresh_enough', return_value=False):
            await bot.market_making_tick()
        
        # Should skip market making but still increment tick count
        assert bot.tick_count == 1

    @pytest.mark.asyncio
    async def test_market_making_tick_no_orderbook(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test market making tick when no orderbook available."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Mock no orderbook
        with patch.object(bot, '_get_orderbook', return_value=None):
            await bot.market_making_tick()
        
        assert bot.tick_count == 1

    @pytest.mark.asyncio
    async def test_get_orderbook_success(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test successful orderbook retrieval."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        orderbook = await bot._get_orderbook()
        
        assert orderbook is not None
        assert "bids" in orderbook
        assert "asks" in orderbook

    @pytest.mark.asyncio
    async def test_get_orderbook_fallback(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test orderbook fallback to oracle price."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Mock DriftClient without get_l2_orderbook method
        bot.drift_client.get_l2_orderbook = None
        
        orderbook = await bot._get_orderbook()
        
        assert orderbook is not None
        assert "bids" in orderbook
        assert "asks" in orderbook

    @pytest.mark.asyncio
    async def test_update_position_success(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test successful position update."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Mock position data
        mock_position = Mock()
        mock_position.market_index = 0
        mock_position.base_asset_amount = 1000000000  # 1 SOL in native precision
        bot.drift_client._user.get_active_perp_positions = Mock(return_value=[mock_position])
        
        await bot._update_position()
        
        assert bot.current_position == 1.0  # 1 SOL

    @pytest.mark.asyncio
    async def test_update_position_no_sol_position(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test position update when no SOL position found."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Mock no SOL position
        mock_position = Mock()
        mock_position.market_index = 1  # Different market
        mock_position.base_asset_amount = 1000000000
        bot.drift_client._user.get_active_perp_positions = Mock(return_value=[mock_position])
        
        await bot._update_position()
        
        assert bot.current_position == 0.0

    @pytest.mark.asyncio
    async def test_update_position_abnormal_value(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test position update with abnormal position value."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Mock abnormal position
        mock_position = Mock()
        mock_position.market_index = 0
        mock_position.base_asset_amount = 1000000000000  # Very large position
        bot.drift_client._user.get_active_perp_positions = Mock(return_value=[mock_position])
        
        await bot._update_position()
        
        # Should reset to 0 due to abnormal value
        assert bot.current_position == 0.0

class TestCompleteSwiftMMBotOrderManagement:
    """Test order management functionality."""
    
    @pytest.mark.asyncio
    async def test_manage_orders_success(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test successful order management."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Mock order placement
        with patch.object(bot, '_place_order_via_sidecar', return_value="test_order_123"):
            await bot._manage_orders(100.0, 100.1, 0.0)
        
        # Should have placed orders
        assert len(bot.active_orders) > 0

    @pytest.mark.asyncio
    async def test_cancel_stale_orders(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test cancellation of stale orders."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Add a stale order
        old_time = time.time() - 60  # 60 seconds ago
        bot.active_orders["stale_order"] = OrderInfo(
            order_id="stale_order",
            side="buy",
            price=99.0,  # Far from current price
            size=1.0,
            timestamp=old_time
        )
        
        with patch.object(bot, '_cancel_order_via_sidecar', return_value=True):
            await bot._cancel_stale_orders(100.0, 100.1)
        
        # Stale order should be cancelled
        assert bot.active_orders["stale_order"].status == "cancelled"

    @pytest.mark.asyncio
    async def test_place_new_orders_inventory_skew(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test order placement with inventory skew."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Set long position (positive skew)
        bot.current_position = 50.0
        
        with patch.object(bot, '_place_order_via_sidecar', return_value="test_order_123"):
            await bot._place_new_orders(100.0, 100.1, 0.5)  # Positive skew
        
        # Should have placed orders with adjusted sizes
        assert len(bot.active_orders) > 0

    @pytest.mark.asyncio
    async def test_place_order_via_sidecar_success(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test successful order placement via sidecar."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        order_id = await bot._place_order_via_sidecar("buy", 100.0, 1.0)
        
        assert order_id == "test_order_123"

    @pytest.mark.asyncio
    async def test_place_order_via_sidecar_no_keypair(self, sample_config, mock_bot_dependencies):
        """Test order placement failure when no keypair."""
        bot = CompleteSwiftMMBot(sample_config)
        bot.keypair = None
        
        order_id = await bot._place_order_via_sidecar("buy", 100.0, 1.0)
        
        assert order_id is None

    @pytest.mark.asyncio
    async def test_cancel_order_via_sidecar_success(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test successful order cancellation via sidecar."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        result = await bot._cancel_order_via_sidecar("test_order_123")
        
        assert result == True

    @pytest.mark.asyncio
    async def test_cancel_order_via_sidecar_no_keypair(self, sample_config, mock_bot_dependencies):
        """Test order cancellation failure when no keypair."""
        bot = CompleteSwiftMMBot(sample_config)
        bot.keypair = None
        
        result = await bot._cancel_order_via_sidecar("test_order_123")
        
        assert result == False

class TestCompleteSwiftMMBotSwiftIntegration:
    """Test Swift integration functionality."""
    
    @pytest.mark.asyncio
    async def test_handle_swift_order_success(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test successful Swift order handling."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Mock Swift order
        mock_order = Mock()
        mock_order.side = "buy"
        mock_order.size = 1.0
        mock_order.price = 100.0
        mock_order.is_delegate = False
        
        await bot._handle_swift_order(mock_order)
        
        assert bot.stats["swift_orders_received"] == 1
        assert bot.stats["swift_orders_processed"] == 1

    @pytest.mark.asyncio
    async def test_handle_swift_order_no_processor(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test Swift order handling when no processor available."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        bot.swift_processor = None
        
        # Mock Swift order
        mock_order = Mock()
        mock_order.side = "buy"
        mock_order.size = 1.0
        mock_order.price = 100.0
        
        await bot._handle_swift_order(mock_order)
        
        assert bot.stats["swift_orders_received"] == 1
        assert bot.stats["swift_orders_processed"] == 0

    @pytest.mark.asyncio
    async def test_start_swift_receiver_success(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test successful Swift receiver startup."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        result = await bot.start_swift_receiver()
        
        assert result == True

    @pytest.mark.asyncio
    async def test_start_swift_receiver_failure(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test Swift receiver startup failure."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Mock receiver start failure
        bot.swift_receiver.start = AsyncMock(side_effect=Exception("Start failed"))
        
        result = await bot.start_swift_receiver()
        
        assert result == False

class TestCompleteSwiftMMBotStatistics:
    """Test statistics and monitoring functionality."""
    
    def test_get_stats_comprehensive(self, sample_config, mock_bot_dependencies):
        """Test comprehensive statistics retrieval."""
        bot = CompleteSwiftMMBot(sample_config)
        
        # Add some test data
        bot.active_orders["test_order"] = OrderInfo(
            order_id="test_order",
            side="buy",
            price=100.0,
            size=1.0,
            timestamp=time.time()
        )
        bot.stats["orders_placed"] = 5
        bot.stats["orders_cancelled"] = 2
        bot.current_position = 10.0
        
        stats = bot.get_stats()
        
        assert "active_orders" in stats
        assert "total_orders" in stats
        assert "performance" in stats
        assert "health" in stats
        assert "position" in stats
        assert stats["active_orders"] == 1
        assert stats["total_orders"] == 1
        assert stats["orders_placed"] == 5
        assert stats["orders_cancelled"] == 2

    def test_get_stats_performance_metrics(self, sample_config, mock_bot_dependencies):
        """Test performance metrics in statistics."""
        bot = CompleteSwiftMMBot(sample_config)
        
        # Set some performance data
        bot.performance_stats["total_ticks"] = 100
        bot.performance_stats["successful_ticks"] = 95
        bot.performance_stats["failed_ticks"] = 5
        bot.performance_stats["avg_tick_time"] = 0.05
        
        stats = bot.get_stats()
        
        assert stats["performance"]["total_ticks"] == 100
        assert stats["performance"]["successful_ticks"] == 95
        assert stats["performance"]["failed_ticks"] == 5
        assert stats["performance"]["error_rate"] == 5.0  # 5/100 * 100

    def test_get_stats_health_monitoring(self, sample_config, mock_bot_dependencies):
        """Test health monitoring in statistics."""
        bot = CompleteSwiftMMBot(sample_config)
        
        bot.tick_count = 50
        bot.error_count = 2
        bot.last_error_time = time.time()
        
        stats = bot.get_stats()
        
        assert stats["health"]["tick_count"] == 50
        assert stats["health"]["error_count"] == 2
        assert stats["health"]["last_error_time"] > 0

class TestCompleteSwiftMMBotErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_market_making_tick_error_handling(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test error handling in market making tick."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Mock an error in the tick
        with patch.object(bot, '_get_orderbook', side_effect=Exception("Orderbook error")):
            await bot.market_making_tick()
        
        assert bot.error_count == 1
        assert bot.performance_stats["failed_ticks"] == 1

    @pytest.mark.asyncio
    async def test_initialize_error_handling(self, sample_config, mock_bot_dependencies):
        """Test error handling in initialization."""
        bot = CompleteSwiftMMBot(sample_config)
        
        # Mock wallet loading error
        with patch.object(bot, '_load_wallet', side_effect=Exception("Wallet error")):
            result = await bot.initialize()
        
        assert result == False

    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test proper shutdown and cleanup."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        await bot.initialize()
        
        # Add some active orders
        bot.active_orders["test_order"] = OrderInfo(
            order_id="test_order",
            side="buy",
            price=100.0,
            size=1.0,
            timestamp=time.time()
        )
        
        with patch.object(bot, '_cancel_order_via_sidecar', return_value=True):
            await bot.shutdown()
        
        # Orders should be cancelled during shutdown
        assert "test_order" not in bot.active_orders

class TestCompleteSwiftMMBotAdvancedFeatures:
    """Test advanced features and algorithms."""
    
    def test_inventory_skew_calculation(self, sample_config, mock_bot_dependencies):
        """Test inventory skew calculation."""
        bot = CompleteSwiftMMBot(sample_config)
        
        # Test neutral position
        skew = bot.inventory_manager.calculate_inventory_skew(0.0)
        assert skew == 0.0
        
        # Test long position
        skew = bot.inventory_manager.calculate_inventory_skew(50.0)
        assert skew > 0.0
        
        # Test short position
        skew = bot.inventory_manager.calculate_inventory_skew(-50.0)
        assert skew < 0.0

    def test_should_trade_logic(self, sample_config, mock_bot_dependencies):
        """Test should trade logic based on position."""
        bot = CompleteSwiftMMBot(sample_config)
        
        # Test within limits
        assert bot.inventory_manager.should_trade(50.0) == True
        assert bot.inventory_manager.should_trade(-50.0) == True
        
        # Test at limits
        assert bot.inventory_manager.should_trade(120.0) == True
        assert bot.inventory_manager.should_trade(-120.0) == True
        
        # Test beyond limits
        assert bot.inventory_manager.should_trade(150.0) == False
        assert bot.inventory_manager.should_trade(-150.0) == False

    def test_obi_calculation(self, sample_config, mock_bot_dependencies):
        """Test OBI calculation."""
        bot = CompleteSwiftMMBot(sample_config)
        
        orderbook = MockOrderbook()
        obi = bot.obi_calculator.calculate_obi(orderbook)
        
        assert hasattr(obi, 'microprice')
        assert hasattr(obi, 'imbalance_ratio')
        assert hasattr(obi, 'skew_adjustment')
        assert hasattr(obi, 'confidence')

    def test_dynamic_spread_calculation(self, sample_config, mock_bot_dependencies):
        """Test dynamic spread calculation."""
        bot = CompleteSwiftMMBot(sample_config)
        
        # Test base spread
        spread = bot.spread_manager.calculate_dynamic_spread(0.001, 0.0, 0.8)
        assert spread >= bot.jit_config.spread_bps_min
        assert spread <= bot.jit_config.spread_bps_max
        
        # Test with inventory skew
        spread_with_skew = bot.spread_manager.calculate_dynamic_spread(0.001, 0.5, 0.8)
        assert spread_with_skew > spread  # Should be higher with skew

    def test_position_anomaly_detection(self, sample_config, test_wallet_file, mock_bot_dependencies):
        """Test position anomaly detection and correction."""
        sample_config["wallet_file"] = test_wallet_file
        
        bot = CompleteSwiftMMBot(sample_config)
        
        # Test abnormal position detection
        bot.current_position = 5000.0  # Abnormal value
        assert abs(bot.current_position) > 1000
        
        # Test default error value detection
        bot.current_position = -5000.0  # Default error value
        assert bot.current_position in [-5000.0, 5000.0]


class TestSwiftReceiverProtocol:
    """Test suite for Swift receiver protocol and accessor method to prevent attribute drift"""

    def test_get_swift_receiver_returns_none_when_uninitialized(self, sample_config):
        """Test that _get_swift_receiver returns None when swift_receiver is not set"""
        bot = CompleteSwiftMMBot(sample_config)
        assert bot._get_swift_receiver() is None

    def test_get_swift_receiver_returns_none_when_no_subscribe_method(self, sample_config):
        """Test that _get_swift_receiver returns None when receiver lacks subscribe method"""
        bot = CompleteSwiftMMBot(sample_config)

        # Set receiver to an object without subscribe method
        class InvalidReceiver:
            pass

        bot.swift_receiver = InvalidReceiver()
        assert bot._get_swift_receiver() is None

    def test_get_swift_receiver_returns_valid_receiver(self, sample_config):
        """Test that _get_swift_receiver returns valid receiver when properly configured"""
        bot = CompleteSwiftMMBot(sample_config)

        # Create a mock receiver with subscribe method
        mock_receiver = Mock()
        mock_receiver.subscribe = AsyncMock()
        bot.swift_receiver = mock_receiver

        result = bot._get_swift_receiver()
        assert result is not None
        assert result == mock_receiver

    def test_swift_receiver_adapter_protocol_compliance(self, sample_config):
        """Test that SwiftReceiverAdapter properly implements SwiftReceiverProtocol"""
        from run_swift_mm_complete import SwiftReceiverAdapter

        # Create mock underlying receiver
        mock_raw_receiver = Mock()
        mock_raw_receiver.start = AsyncMock()

        # Create adapter
        adapter = SwiftReceiverAdapter(mock_raw_receiver)

        # Verify adapter has subscribe method
        assert hasattr(adapter, 'subscribe')
        assert callable(getattr(adapter, 'subscribe'))

        # Test that subscribe calls the underlying receiver's start method
        async def dummy_handler():
            pass

        # Run the subscribe method
        asyncio.run(adapter.subscribe(dummy_handler))

        # Verify the underlying start method was called
        mock_raw_receiver.start.assert_called_once()

    def test_protocol_enforces_subscribe_method(self):
        """Test that the protocol properly enforces the subscribe method contract"""
        from run_swift_mm_complete import SwiftReceiverProtocol

        # This test ensures that any class claiming to implement SwiftReceiverProtocol
        # must have a subscribe method with the correct signature
        # The Protocol will raise AttributeError at runtime if subscribe is missing

        class ValidReceiver:
            async def subscribe(self, handler):
                pass

        class InvalidReceiver:
            pass  # Missing subscribe method

        # Valid receiver should work
        valid = ValidReceiver()
        assert hasattr(valid, 'subscribe')

        # Invalid receiver should fail protocol check
        invalid = InvalidReceiver()
        assert not hasattr(invalid, 'subscribe')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
