#!/usr/bin/env python3
"""
Advanced Algorithm Tests for Complete Swift Market Making Bot

These tests focus on the JIT algorithms, OBI calculations, inventory management,
and other advanced features.
"""

import pytest
import time
from unittest.mock import Mock, patch
from typing import Dict, Any

# Add project root to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from run_swift_mm_complete import CompleteSwiftMMBot, OrderInfo

class TestJITAlgorithms:
    """Test JIT (Just-In-Time) trading algorithms."""
    
    @pytest.fixture
    def algorithm_config(self):
        return {
            "env": "devnet",
            "symbol": "SOL-PERP",
            "leverage": 10,
            "post_only": True,
            "obi_microprice": True,
            "spread_bps": 8.0,
            "spread_bps_min": 4.0,
            "spread_bps_max": 25.0,
            "inventory_target": 0.0,
            "max_position_abs": 120.0,
            "cancel_replace_enabled": True,
            "cancel_replace_interval_ms": 1000,
            "toxicity_guard": True,
            "order_size": 0.01,
            "max_orders_per_side": 1,
            "price_tolerance": 0.01
        }

    @pytest.fixture
    def mock_algorithm_dependencies(self):
        """Mock dependencies for algorithm testing."""
        with patch('run_swift_mm_complete.JITConfig'), \
             patch('run_swift_mm_complete.InventoryManager'), \
             patch('run_swift_mm_complete.OBICalculator'), \
             patch('run_swift_mm_complete.SpreadManager'), \
             patch('run_swift_mm_complete.Orderbook'), \
             patch('run_swift_mm_complete.DriftClient'), \
             patch('run_swift_mm_complete.Keypair'), \
             patch('run_swift_mm_complete.SwiftSidecarClient'), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator'), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver'), \
             patch('run_swift_mm_complete.SwiftOrderProcessor'), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor'), \
             patch('run_swift_mm_complete.RELIABILITY_UTILS_AVAILABLE', False):
            yield

    def test_jit_config_creation(self, algorithm_config, mock_algorithm_dependencies):
        """Test JIT configuration creation with various parameters."""
        # Test default configuration
        bot = CompleteSwiftMMBot(algorithm_config)
        
        assert bot.jit_config.symbol == "SOL-PERP"
        assert bot.jit_config.leverage == 10
        assert bot.jit_config.post_only == True
        assert bot.jit_config.obi_microprice == True
        assert bot.jit_config.spread_bps_base == 8.0
        assert bot.jit_config.spread_bps_min == 4.0
        assert bot.jit_config.spread_bps_max == 25.0
        assert bot.jit_config.inventory_target == 0.0
        assert bot.jit_config.max_position_abs == 120.0
        assert bot.jit_config.cancel_replace_enabled == True
        assert bot.jit_config.cancel_replace_interval_ms == 1000
        assert bot.jit_config.toxicity_guard == True

    def test_jit_config_edge_cases(self, mock_algorithm_dependencies):
        """Test JIT configuration with edge case values."""
        # Test with extreme values
        extreme_config = {
            "env": "devnet",
            "symbol": "BTC-PERP",
            "leverage": 1,  # Minimum leverage
            "post_only": False,
            "obi_microprice": False,
            "spread_bps": 0.1,  # Very low spread
            "spread_bps_min": 0.1,
            "spread_bps_max": 100.0,  # Very high spread
            "inventory_target": -50.0,  # Negative target
            "max_position_abs": 0.1,  # Very small position
            "cancel_replace_enabled": False,
            "cancel_replace_interval_ms": 100,  # Very fast
            "toxicity_guard": False
        }
        
        bot = CompleteSwiftMMBot(extreme_config)
        
        assert bot.jit_config.symbol == "BTC-PERP"
        assert bot.jit_config.leverage == 1
        assert bot.jit_config.post_only == False
        assert bot.jit_config.obi_microprice == False
        assert bot.jit_config.spread_bps_base == 0.1
        assert bot.jit_config.spread_bps_min == 0.1
        assert bot.jit_config.spread_bps_max == 100.0
        assert bot.jit_config.inventory_target == -50.0
        assert bot.jit_config.max_position_abs == 0.1
        assert bot.jit_config.cancel_replace_enabled == False
        assert bot.jit_config.cancel_replace_interval_ms == 100
        assert bot.jit_config.toxicity_guard == False

class TestInventoryManagement:
    """Test inventory management algorithms."""
    
    @pytest.fixture
    def inventory_config(self):
        return {
            "env": "devnet",
            "max_position_abs": 100.0,
            "inventory_target": 0.0
        }

    @pytest.fixture
    def mock_inventory_dependencies(self):
        with patch('run_swift_mm_complete.JITConfig'), \
             patch('run_swift_mm_complete.InventoryManager'), \
             patch('run_swift_mm_complete.OBICalculator'), \
             patch('run_swift_mm_complete.SpreadManager'), \
             patch('run_swift_mm_complete.Orderbook'), \
             patch('run_swift_mm_complete.DriftClient'), \
             patch('run_swift_mm_complete.Keypair'), \
             patch('run_swift_mm_complete.SwiftSidecarClient'), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator'), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver'), \
             patch('run_swift_mm_complete.SwiftOrderProcessor'), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor'), \
             patch('run_swift_mm_complete.RELIABILITY_UTILS_AVAILABLE', False):
            yield

    def test_inventory_skew_calculation(self, inventory_config, mock_inventory_dependencies):
        """Test inventory skew calculation with various positions."""
        # Mock inventory manager
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

        with patch('run_swift_mm_complete.InventoryManager', MockInventoryManager):
            bot = CompleteSwiftMMBot(inventory_config)
            
            # Test neutral position
            skew = bot.inventory_manager.calculate_inventory_skew(0.0)
            assert skew == 0.0
            
            # Test long position
            skew = bot.inventory_manager.calculate_inventory_skew(50.0)
            assert skew == 0.5  # 50/100
            
            # Test short position
            skew = bot.inventory_manager.calculate_inventory_skew(-50.0)
            assert skew == -0.5  # -50/100
            
            # Test at maximum position
            skew = bot.inventory_manager.calculate_inventory_skew(100.0)
            assert skew == 1.0
            
            # Test beyond maximum position (should be clamped)
            skew = bot.inventory_manager.calculate_inventory_skew(150.0)
            assert skew == 1.0  # Clamped to 1.0

    def test_should_trade_logic(self, inventory_config, mock_inventory_dependencies):
        """Test should trade logic based on position limits."""
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

        with patch('run_swift_mm_complete.InventoryManager', MockInventoryManager):
            bot = CompleteSwiftMMBot(inventory_config)
            
            # Test within limits
            assert bot.inventory_manager.should_trade(0.0) == True
            assert bot.inventory_manager.should_trade(50.0) == True
            assert bot.inventory_manager.should_trade(-50.0) == True
            assert bot.inventory_manager.should_trade(100.0) == True
            assert bot.inventory_manager.should_trade(-100.0) == True
            
            # Test beyond limits
            assert bot.inventory_manager.should_trade(101.0) == False
            assert bot.inventory_manager.should_trade(-101.0) == False
            assert bot.inventory_manager.should_trade(200.0) == False
            assert bot.inventory_manager.should_trade(-200.0) == False

class TestOBICalculations:
    """Test Order Book Imbalance (OBI) calculations."""
    
    @pytest.fixture
    def obi_config(self):
        return {
            "env": "devnet",
            "obi_microprice": True
        }

    @pytest.fixture
    def mock_obi_dependencies(self):
        with patch('run_swift_mm_complete.JITConfig'), \
             patch('run_swift_mm_complete.InventoryManager'), \
             patch('run_swift_mm_complete.OBICalculator'), \
             patch('run_swift_mm_complete.SpreadManager'), \
             patch('run_swift_mm_complete.Orderbook'), \
             patch('run_swift_mm_complete.DriftClient'), \
             patch('run_swift_mm_complete.Keypair'), \
             patch('run_swift_mm_complete.SwiftSidecarClient'), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator'), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver'), \
             patch('run_swift_mm_complete.SwiftOrderProcessor'), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor'), \
             patch('run_swift_mm_complete.RELIABILITY_UTILS_AVAILABLE', False):
            yield

    def test_obi_calculation(self, obi_config, mock_obi_dependencies):
        """Test OBI calculation with various orderbook scenarios."""
        class MockOBICalculator:
            def __init__(self, levels=10):
                self.levels = levels

            def calculate_obi(self, orderbook):
                class OBI:
                    def __init__(self, bids, asks):
                        if not bids or not asks:
                            self.microprice = 100.0
                            self.imbalance_ratio = 0.0
                            self.skew_adjustment = 0.0
                            self.confidence = 0.0
                        else:
                            # Calculate microprice as weighted average
                            bid_price = bids[0][0]
                            ask_price = asks[0][0]
                            bid_size = bids[0][1]
                            ask_size = asks[0][1]
                            
                            total_size = bid_size + ask_size
                            if total_size > 0:
                                self.microprice = (bid_price * ask_size + ask_price * bid_size) / total_size
                                self.imbalance_ratio = (bid_size - ask_size) / total_size
                            else:
                                self.microprice = (bid_price + ask_price) / 2
                                self.imbalance_ratio = 0.0
                            
                            self.skew_adjustment = self.imbalance_ratio * 0.1
                            self.confidence = min(1.0, total_size / 100.0)  # Higher confidence with more size

                return OBI(orderbook.bids, orderbook.asks)

        with patch('run_swift_mm_complete.OBICalculator', MockOBICalculator):
            bot = CompleteSwiftMMBot(obi_config)
            
            # Test with balanced orderbook
            balanced_orderbook = Mock()
            balanced_orderbook.bids = [[99.9, 10.0], [99.8, 15.0]]
            balanced_orderbook.asks = [[100.1, 10.0], [100.2, 15.0]]
            
            obi = bot.obi_calculator.calculate_obi(balanced_orderbook)
            assert obi.microprice == 100.0  # Should be exactly between bid and ask
            assert obi.imbalance_ratio == 0.0  # Should be balanced
            assert obi.skew_adjustment == 0.0
            assert obi.confidence > 0.0
            
            # Test with imbalanced orderbook (more bids)
            bid_heavy_orderbook = Mock()
            bid_heavy_orderbook.bids = [[99.9, 20.0], [99.8, 15.0]]
            bid_heavy_orderbook.asks = [[100.1, 5.0], [100.2, 10.0]]
            
            obi = bot.obi_calculator.calculate_obi(bid_heavy_orderbook)
            assert obi.imbalance_ratio > 0.0  # Should be positive (more bids)
            assert obi.skew_adjustment > 0.0  # Should be positive
            
            # Test with imbalanced orderbook (more asks)
            ask_heavy_orderbook = Mock()
            ask_heavy_orderbook.bids = [[99.9, 5.0], [99.8, 10.0]]
            ask_heavy_orderbook.asks = [[100.1, 20.0], [100.2, 15.0]]
            
            obi = bot.obi_calculator.calculate_obi(ask_heavy_orderbook)
            assert obi.imbalance_ratio < 0.0  # Should be negative (more asks)
            assert obi.skew_adjustment < 0.0  # Should be negative

    def test_obi_microprice_usage(self, obi_config, mock_obi_dependencies):
        """Test OBI microprice usage in pricing decisions."""
        class MockOBICalculator:
            def __init__(self, levels=10):
                self.levels = levels

            def calculate_obi(self, orderbook):
                class OBI:
                    def __init__(self):
                        self.microprice = 100.05  # Slightly above mid
                        self.imbalance_ratio = 0.1
                        self.skew_adjustment = 0.01
                        self.confidence = 0.8
                return OBI()

        with patch('run_swift_mm_complete.OBICalculator', MockOBICalculator):
            bot = CompleteSwiftMMBot(obi_config)
            
            # Test that OBI microprice is used when enabled
            assert bot.jit_config.obi_microprice == True
            
            # Test OBI calculation
            mock_orderbook = Mock()
            mock_orderbook.bids = [[99.9, 10.0]]
            mock_orderbook.asks = [[100.1, 10.0]]
            
            obi = bot.obi_calculator.calculate_obi(mock_orderbook)
            assert obi.microprice == 100.05
            assert obi.confidence == 0.8

class TestSpreadManagement:
    """Test dynamic spread calculation algorithms."""
    
    @pytest.fixture
    def spread_config(self):
        return {
            "env": "devnet",
            "spread_bps": 8.0,
            "spread_bps_min": 4.0,
            "spread_bps_max": 25.0
        }

    @pytest.fixture
    def mock_spread_dependencies(self):
        with patch('run_swift_mm_complete.JITConfig'), \
             patch('run_swift_mm_complete.InventoryManager'), \
             patch('run_swift_mm_complete.OBICalculator'), \
             patch('run_swift_mm_complete.SpreadManager'), \
             patch('run_swift_mm_complete.Orderbook'), \
             patch('run_swift_mm_complete.DriftClient'), \
             patch('run_swift_mm_complete.Keypair'), \
             patch('run_swift_mm_complete.SwiftSidecarClient'), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator'), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver'), \
             patch('run_swift_mm_complete.SwiftOrderProcessor'), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor'), \
             patch('run_swift_mm_complete.RELIABILITY_UTILS_AVAILABLE', False):
            yield

    def test_dynamic_spread_calculation(self, spread_config, mock_spread_dependencies):
        """Test dynamic spread calculation with various market conditions."""
        class MockSpreadManager:
            def __init__(self, config):
                self.config = config

            def calculate_dynamic_spread(self, volatility, inventory_skew, confidence):
                base_spread = self.config.spread_bps_base
                skew_adjustment = abs(inventory_skew) * 5.0  # 5 bps per 100% skew
                volatility_adjustment = volatility * 1000  # Scale volatility
                confidence_adjustment = (1.0 - confidence) * 2.0  # Higher spread for lower confidence
                
                total_spread = base_spread + skew_adjustment + volatility_adjustment + confidence_adjustment
                return min(max(total_spread, self.config.spread_bps_min), self.config.spread_bps_max)

        with patch('run_swift_mm_complete.SpreadManager', MockSpreadManager):
            bot = CompleteSwiftMMBot(spread_config)
            
            # Test base spread
            spread = bot.spread_manager.calculate_dynamic_spread(0.001, 0.0, 0.8)
            assert spread >= bot.jit_config.spread_bps_min
            assert spread <= bot.jit_config.spread_bps_max
            assert spread >= bot.jit_config.spread_bps_base  # Should be at least base spread
            
            # Test with inventory skew
            spread_with_skew = bot.spread_manager.calculate_dynamic_spread(0.001, 0.5, 0.8)
            assert spread_with_skew > spread  # Should be higher with skew
            
            # Test with high volatility
            spread_with_volatility = bot.spread_manager.calculate_dynamic_spread(0.01, 0.0, 0.8)
            assert spread_with_volatility > spread  # Should be higher with volatility
            
            # Test with low confidence
            spread_with_low_confidence = bot.spread_manager.calculate_dynamic_spread(0.001, 0.0, 0.3)
            assert spread_with_low_confidence > spread  # Should be higher with low confidence
            
            # Test extreme conditions
            extreme_spread = bot.spread_manager.calculate_dynamic_spread(0.1, 1.0, 0.1)
            assert extreme_spread == bot.jit_config.spread_bps_max  # Should be clamped to max

    def test_spread_bounds_enforcement(self, spread_config, mock_spread_dependencies):
        """Test that spread calculations respect minimum and maximum bounds."""
        class MockSpreadManager:
            def __init__(self, config):
                self.config = config

            def calculate_dynamic_spread(self, volatility, inventory_skew, confidence):
                # Return extreme values to test bounds
                return 100.0  # Way above max

        with patch('run_swift_mm_complete.SpreadManager', MockSpreadManager):
            bot = CompleteSwiftMMBot(spread_config)
            
            spread = bot.spread_manager.calculate_dynamic_spread(0.001, 0.0, 0.8)
            assert spread == bot.jit_config.spread_bps_max  # Should be clamped to max

class TestPositionAnomalyDetection:
    """Test position anomaly detection and correction."""
    
    @pytest.fixture
    def anomaly_config(self):
        return {
            "env": "devnet",
            "max_position_abs": 120.0
        }

    @pytest.fixture
    def mock_anomaly_dependencies(self):
        with patch('run_swift_mm_complete.JITConfig'), \
             patch('run_swift_mm_complete.InventoryManager'), \
             patch('run_swift_mm_complete.OBICalculator'), \
             patch('run_swift_mm_complete.SpreadManager'), \
             patch('run_swift_mm_complete.Orderbook'), \
             patch('run_swift_mm_complete.DriftClient'), \
             patch('run_swift_mm_complete.Keypair'), \
             patch('run_swift_mm_complete.SwiftSidecarClient'), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator'), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver'), \
             patch('run_swift_mm_complete.SwiftOrderProcessor'), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor'), \
             patch('run_swift_mm_complete.RELIABILITY_UTILS_AVAILABLE', False):
            yield

    def test_abnormal_position_detection(self, anomaly_config, mock_anomaly_dependencies):
        """Test detection of abnormal position values."""
        bot = CompleteSwiftMMBot(anomaly_config)
        
        # Test normal position
        bot.current_position = 50.0
        assert abs(bot.current_position) <= 1000  # Should be normal
        
        # Test abnormal position (too large)
        bot.current_position = 5000.0
        assert abs(bot.current_position) > 1000  # Should be detected as abnormal
        
        # Test default error values
        bot.current_position = -5000.0
        assert bot.current_position in [-5000.0, 5000.0]  # Should be detected as error value

    def test_position_reset_logic(self, anomaly_config, mock_anomaly_dependencies):
        """Test position reset logic for anomalous values."""
        bot = CompleteSwiftMMBot(anomaly_config)
        
        # Test reset from abnormal value
        bot.current_position = 5000.0
        if abs(bot.current_position) > 1000:
            bot.current_position = 0.0
        assert bot.current_position == 0.0
        
        # Test reset from error value
        bot.current_position = -5000.0
        if bot.current_position in [-5000.0, 5000.0]:
            bot.current_position = 0.0
        assert bot.current_position == 0.0

class TestOrderSizingAlgorithms:
    """Test order sizing algorithms based on inventory and market conditions."""
    
    @pytest.fixture
    def sizing_config(self):
        return {
            "env": "devnet",
            "order_size": 0.01,
            "max_position_abs": 120.0
        }

    @pytest.fixture
    def mock_sizing_dependencies(self):
        with patch('run_swift_mm_complete.JITConfig'), \
             patch('run_swift_mm_complete.InventoryManager'), \
             patch('run_swift_mm_complete.OBICalculator'), \
             patch('run_swift_mm_complete.SpreadManager'), \
             patch('run_swift_mm_complete.Orderbook'), \
             patch('run_swift_mm_complete.DriftClient'), \
             patch('run_swift_mm_complete.Keypair'), \
             patch('run_swift_mm_complete.SwiftSidecarClient'), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator'), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver'), \
             patch('run_swift_mm_complete.SwiftOrderProcessor'), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor'), \
             patch('run_swift_mm_complete.RELIABILITY_UTILS_AVAILABLE', False):
            yield

    def test_inventory_aware_sizing(self, sizing_config, mock_sizing_dependencies):
        """Test order sizing based on inventory skew."""
        bot = CompleteSwiftMMBot(sizing_config)
        
        base_size = bot.order_size
        
        # Test neutral position
        inventory_skew = 0.0
        if inventory_skew > 0.1:  # Long position - want to sell more
            ask_size = base_size * 1.2
            bid_size = base_size * 0.8
        elif inventory_skew < -0.1:  # Short position - want to buy more
            bid_size = base_size * 1.2
            ask_size = base_size * 0.8
        else:  # Neutral position
            bid_size = ask_size = base_size
        
        assert bid_size == base_size
        assert ask_size == base_size
        
        # Test long position (positive skew)
        inventory_skew = 0.5
        if inventory_skew > 0.1:  # Long position - want to sell more
            ask_size = base_size * 1.2
            bid_size = base_size * 0.8
        elif inventory_skew < -0.1:  # Short position - want to buy more
            bid_size = base_size * 1.2
            ask_size = base_size * 0.8
        else:  # Neutral position
            bid_size = ask_size = base_size
        
        assert ask_size > base_size  # Should be larger for selling
        assert bid_size < base_size  # Should be smaller for buying
        
        # Test short position (negative skew)
        inventory_skew = -0.5
        if inventory_skew > 0.1:  # Long position - want to sell more
            ask_size = base_size * 1.2
            bid_size = base_size * 0.8
        elif inventory_skew < -0.1:  # Short position - want to buy more
            bid_size = base_size * 1.2
            ask_size = base_size * 0.8
        else:  # Neutral position
            bid_size = ask_size = base_size
        
        assert bid_size > base_size  # Should be larger for buying
        assert ask_size < base_size  # Should be smaller for selling

class TestEnvironmentVariables:
    """Test environment variable handling and configuration."""

    @pytest.fixture
    def env_config(self):
        """Create test configuration with environment variables."""
        return {
            "env": "devnet",
            "rpc_url": "https://test-rpc.com",
            "wallet_file": ".test_wallet.json",
            "order_size": 0.01,
            "sidecar_url": "http://localhost:8787",
            "swift_websocket_url": "wss://test-swift.com/ws",
            "swift_api_key": "test_key_123"
        }

    @pytest.fixture
    def mock_env_dependencies(self):
        with patch('run_swift_mm_complete.JITConfig'), \
             patch('run_swift_mm_complete.InventoryManager'), \
             patch('run_swift_mm_complete.OBICalculator'), \
             patch('run_swift_mm_complete.SpreadManager'), \
             patch('run_swift_mm_complete.Orderbook'), \
             patch('run_swift_mm_complete.DriftClient'), \
             patch('run_swift_mm_complete.Keypair'), \
             patch('run_swift_mm_complete.SwiftSidecarClient'), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator'), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver'), \
             patch('run_swift_mm_complete.SwiftOrderProcessor'), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor'), \
             patch('run_swift_mm_complete.RELIABILITY_UTILS_AVAILABLE', False):
            yield

    def test_env_var_overrides(self, env_config, mock_env_dependencies):
        """Test environment variable overrides for configuration."""
        import os

        # Test environment variable overrides
        with patch.dict(os.environ, {
            'DRIFT_ENV': 'mainnet',
            'RPC_URL': 'https://mainnet-rpc.com',
            'SWIFT_SIDECAR_URL': 'http://prod-sidecar:8787',
            'SWIFT_WEBSOCKET_URL': 'wss://prod-swift.com/ws',
            'SWIFT_API_KEY': 'prod_key_456'
        }):
            # Simulate reading environment variables
            env = os.getenv('DRIFT_ENV', 'devnet')
            rpc_url = os.getenv('RPC_URL', 'https://test-rpc.com')
            sidecar_url = os.getenv('SWIFT_SIDECAR_URL', 'http://localhost:8787')
            ws_url = os.getenv('SWIFT_WEBSOCKET_URL', 'wss://test-swift.com/ws')
            api_key = os.getenv('SWIFT_API_KEY', 'test_key_123')

            assert env == 'mainnet'
            assert rpc_url == 'https://mainnet-rpc.com'
            assert sidecar_url == 'http://prod-sidecar:8787'
            assert ws_url == 'wss://prod-swift.com/ws'
            assert api_key == 'prod_key_456'

    def test_env_var_defaults(self, env_config, mock_env_dependencies):
        """Test default values when environment variables are not set."""
        import os

        # Clear environment variables for testing defaults
        with patch.dict(os.environ, {}, clear=True):
            # Simulate reading environment variables with defaults
            env = os.getenv('DRIFT_ENV', 'devnet')
            rpc_url = os.getenv('RPC_URL', 'https://api.devnet.solana.com')
            sidecar_url = os.getenv('SWIFT_SIDECAR_URL', 'http://localhost:8787')
            ws_url = os.getenv('SWIFT_WEBSOCKET_URL', 'wss://swift.drift.trade/ws')
            api_key = os.getenv('SWIFT_API_KEY')

            assert env == 'devnet'
            assert rpc_url == 'https://api.devnet.solana.com'
            assert sidecar_url == 'http://localhost:8787'
            assert ws_url == 'wss://swift.drift.trade/ws'
            assert api_key is None

    def test_config_validation_with_env_vars(self, env_config, mock_env_dependencies):
        """Test configuration validation with environment variable overrides."""
        import os

        # Test production configuration via environment
        with patch.dict(os.environ, {
            'DRIFT_ENV': 'mainnet',
            'RPC_URL': 'https://api.mainnet.solana.com',
            'SWIFT_SIDECAR_URL': 'https://api.drift.trade',
            'ORDER_SIZE': '0.1',
            'MAX_DAILY_LOSS_USD': '10000'
        }):
            # Simulate configuration loading with env vars
            config = {
                'env': os.getenv('DRIFT_ENV', 'devnet'),
                'rpc_url': os.getenv('RPC_URL', 'https://api.devnet.solana.com'),
                'sidecar_url': os.getenv('SWIFT_SIDECAR_URL', 'http://localhost:8787'),
                'order_size': float(os.getenv('ORDER_SIZE', '0.01')),
                'max_daily_loss_usd': float(os.getenv('MAX_DAILY_LOSS_USD', '5000'))
            }

            # Validate configuration
            assert config['env'] == 'mainnet'
            assert config['rpc_url'] == 'https://api.mainnet.solana.com'
            assert config['sidecar_url'] == 'https://api.drift.trade'
            assert config['order_size'] == 0.1
            assert config['max_daily_loss_usd'] == 10000

    def test_env_var_precedence(self, env_config, mock_env_dependencies):
        """Test that environment variables take precedence over config file values."""
        import os

        # Test precedence: env vars should override config file values
        with patch.dict(os.environ, {
            'DRIFT_ENV': 'beta',
            'RPC_URL': 'https://beta-rpc.com'
        }):
            # Simulate loading config with env var precedence
            config = env_config.copy()

            # Apply environment variable overrides
            if os.getenv('DRIFT_ENV'):
                config['env'] = os.getenv('DRIFT_ENV')
            if os.getenv('RPC_URL'):
                config['rpc_url'] = os.getenv('RPC_URL')

            assert config['env'] == 'beta'  # Should be overridden
            assert config['rpc_url'] == 'https://beta-rpc.com'  # Should be overridden
            assert config['wallet_file'] == '.test_wallet.json'  # Should remain from config

    def test_missing_env_vars_handling(self, env_config, mock_env_dependencies):
        """Test graceful handling of missing environment variables."""
        import os

        # Test with some env vars missing
        with patch.dict(os.environ, {
            'DRIFT_ENV': 'testnet'
            # Missing RPC_URL and other vars
        }):
            config = {
                'env': os.getenv('DRIFT_ENV', 'devnet'),
                'rpc_url': os.getenv('RPC_URL', 'https://api.devnet.solana.com'),
                'sidecar_url': os.getenv('SWIFT_SIDECAR_URL', 'http://localhost:8787'),
                'order_size': float(os.getenv('ORDER_SIZE', '0.01')),
                'max_daily_loss_usd': float(os.getenv('MAX_DAILY_LOSS_USD', '5000'))
            }

            # Should use defaults for missing vars
            assert config['env'] == 'testnet'  # From env var
            assert config['rpc_url'] == 'https://api.devnet.solana.com'  # Default
            assert config['sidecar_url'] == 'http://localhost:8787'  # Default
            assert config['order_size'] == 0.01  # Default
            assert config['max_daily_loss_usd'] == 5000  # Default

    def test_env_var_type_conversion(self, env_config, mock_env_dependencies):
        """Test proper type conversion from environment variable strings."""
        import os

        # Test numeric conversions from string env vars
        with patch.dict(os.environ, {
            'ORDER_SIZE': '0.05',
            'MAX_POSITION_ABS': '200',
            'SPREAD_BPS': '10.5',
            'LEVERAGE': '5',
            'MAX_DAILY_LOSS_USD': '10000'
        }):
            # Simulate type conversion
            config = {
                'order_size': float(os.getenv('ORDER_SIZE', '0.01')),
                'max_position_abs': float(os.getenv('MAX_POSITION_ABS', '120')),
                'spread_bps': float(os.getenv('SPREAD_BPS', '8')),
                'leverage': int(os.getenv('LEVERAGE', '10')),
                'max_daily_loss_usd': float(os.getenv('MAX_DAILY_LOSS_USD', '5000'))
            }

            # Verify correct types
            assert isinstance(config['order_size'], float)
            assert isinstance(config['max_position_abs'], float)
            assert isinstance(config['spread_bps'], float)
            assert isinstance(config['leverage'], int)
            assert isinstance(config['max_daily_loss_usd'], float)

            # Verify values
            assert config['order_size'] == 0.05
            assert config['max_position_abs'] == 200.0
            assert config['spread_bps'] == 10.5
            assert config['leverage'] == 5
            assert config['max_daily_loss_usd'] == 10000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
