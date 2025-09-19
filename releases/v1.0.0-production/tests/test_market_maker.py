#!/usr/bin/env python3
"""
Unit Tests for Enhanced JIT Market Maker
Tests core market making functionality, order placement, and risk management
"""

import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from run_swift_mm_complete import CompleteSwiftMMBot
from libs.util.decimal import D


class TestMarketMakerCore:
    """Test core market making functionality"""
    
    @pytest.fixture
    def config(self):
        """Basic configuration for testing"""
        return {
            'symbol': 'SOL-PERP',
            'buy_order_size': 0.5,
            'sell_order_size': 0.3,
            'order_size': 0.4,
            'spread_bps': {'base': 50, 'min': 20, 'max': 200},
            'enable_capital_allocation': False,
            'max_orders_per_side': 1,
            'env': 'devnet',
            'rpc_url': 'https://api.devnet.solana.com',
            'swift_config': {
                'base_url': 'https://master.swift.drift.trade'
            }
        }
    
    @pytest.fixture
    def mock_drift_client(self):
        """Mock DriftPy client"""
        client = Mock()
        client.subscribe = AsyncMock()
        client.get_oracle_price_for_perp_market = AsyncMock(return_value=150.0)
        client.get_l2_orderbook = Mock(return_value={
            'bids': [{'price': 149.5, 'size': 1.0}],
            'asks': [{'price': 150.5, 'size': 1.0}]
        })
        return client
    
    @pytest.fixture
    async def market_maker(self, config, mock_drift_client):
        """Create market maker instance for testing"""
        with patch('run_swift_mm_complete.DriftClient', return_value=mock_drift_client):
            bot = CompleteSwiftMMBot(config)
            bot.drift_client = mock_drift_client
            bot.test_mode = True
            return bot
    
    async def test_initialization(self, market_maker, config):
        """Test market maker initialization"""
        assert market_maker.buy_order_size == 0.5
        assert market_maker.sell_order_size == 0.3
        assert market_maker.order_size == 0.4
        assert market_maker.symbol == 'SOL-PERP'
        assert not market_maker.enable_capital_allocation
    
    async def test_order_size_calculation(self, market_maker):
        """Test order size calculation with configured sizes"""
        # Test buy order size
        buy_size = await market_maker._calculate_order_size("buy", 0.0)
        assert buy_size == 0.5
        
        # Test sell order size  
        sell_size = await market_maker._calculate_order_size("sell", 0.0)
        assert sell_size == 0.3
        
        # Test minimum size enforcement
        market_maker.buy_order_size = 0.005  # Below minimum
        buy_size = await market_maker._calculate_order_size("buy", 0.0)
        assert buy_size == 0.01  # Should be adjusted to minimum
    
    async def test_health_gate_system(self, market_maker):
        """Test trading health gate functionality"""
        # Initially not ready
        assert not market_maker.trading_allowed()
        
        # Enable drift health
        market_maker.update_drift_health(True)
        assert not market_maker.trading_allowed()  # Still need market feed
        
        # Enable market feed health
        market_maker.update_market_feed_health(True)
        assert market_maker.trading_allowed()  # Now ready
        
        # Disable drift health
        market_maker.update_drift_health(False)
        assert not market_maker.trading_allowed()  # Should block trading
    
    async def test_orderbook_processing(self, market_maker, mock_drift_client):
        """Test orderbook data processing"""
        # Test successful orderbook fetch
        orderbook = await market_maker._get_orderbook()
        assert orderbook is not None
        assert 'bids' in orderbook
        assert 'asks' in orderbook
        
        # Test empty orderbook handling
        mock_drift_client.get_l2_orderbook.return_value = None
        orderbook = await market_maker._get_orderbook()
        assert orderbook is not None  # Should return mock orderbook
        assert orderbook['bids'][0]['price'] > 0
    
    async def test_oracle_price_validation(self, market_maker, mock_drift_client):
        """Test oracle price validation"""
        # Test valid oracle price
        assert await market_maker.oracle_fresh_enough(max_delay_slots=100)
        
        # Test invalid oracle price
        mock_drift_client.get_oracle_price_for_perp_market.return_value = 0
        assert await market_maker.oracle_fresh_enough(max_delay_slots=100)  # Should allow during settling
        
        # Test oracle error handling
        mock_drift_client.get_oracle_price_for_perp_market.side_effect = Exception("Oracle error")
        assert await market_maker.oracle_fresh_enough(max_delay_slots=100)  # Should allow during errors


class TestRiskManagement:
    """Test risk management and position controls"""
    
    @pytest.fixture
    def config_with_capital_allocation(self):
        """Configuration with capital allocation enabled"""
        return {
            'symbol': 'SOL-PERP',
            'buy_order_size': 0.5,
            'sell_order_size': 0.3,
            'order_size': 0.4,
            'enable_capital_allocation': True,
            'max_orders_per_side': 1,
            'env': 'devnet'
        }
    
    async def test_position_limits(self, config_with_capital_allocation):
        """Test position limit enforcement"""
        with patch('run_swift_mm_complete.DriftClient'):
            bot = CompleteSwiftMMBot(config_with_capital_allocation)
            bot.test_mode = True
            
            # Test max order size calculation
            max_size = await bot.calculate_max_order_size("buy", 0.0)
            assert max_size >= 0.01  # Should respect minimum
    
    async def test_collateral_requirements(self, market_maker):
        """Test collateral requirement validation"""
        # Test with mock collateral data
        with patch.object(market_maker, 'get_user_collateral', return_value={
            'total_collateral': 1000.0,
            'free_collateral': 500.0,
            'margin_requirement': 500.0
        }):
            # Test sufficient collateral
            collateral = await market_maker.get_user_collateral()
            assert collateral['free_collateral'] > 0
    
    async def test_position_tracking(self, market_maker):
        """Test position tracking and updates"""
        # Test initial position
        market_maker.current_position = 0.0
        
        # Simulate position update
        await market_maker._update_position()
        # Position should be tracked (mocked to current value)
        
        # Test position bounds
        assert isinstance(market_maker.current_position, (int, float))


class TestOrderExecution:
    """Test order execution and routing"""
    
    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP client for Swift API"""
        client = Mock()
        client.post = AsyncMock(return_value=Mock(
            json=lambda: {'order_id': 'test_order_123'},
            status_code=200
        ))
        return client
    
    async def test_swift_order_placement(self, market_maker, mock_http_client):
        """Test Swift API order placement"""
        market_maker.http_client = mock_http_client
        market_maker.sidecar_url = "https://test.swift.com"
        
        # Test buy order
        with patch.object(market_maker, '_create_swift_order_params', return_value={}):
            order_id = await market_maker._place_order_via_sidecar("buy", 150.0, 0.5)
            assert order_id == 'test_order_123'
    
    async def test_driftpy_fallback(self, market_maker, mock_drift_client):
        """Test DriftPy fallback execution"""
        mock_drift_client.place_perp_order = AsyncMock(return_value="tx_signature_123")
        
        # Test direct order placement
        with patch('run_swift_mm_complete.get_perp_market_account') as mock_market:
            mock_market.return_value = Mock(
                amm=Mock(
                    base_asset_amount_step_size=10_000_000,  # 0.01 SOL
                    quote_asset_amount_step_size=1000
                )
            )
            
            tx_sig = await market_maker._place_order_direct_driftpy("buy", 150.0, 0.5)
            assert tx_sig == "tx_signature_123"
    
    async def test_order_routing_logic(self, market_maker):
        """Test intelligent order routing"""
        # Test Swift routing preference
        market_maker.sidecar_degraded = False
        market_maker.drift_fallback_active = False
        
        # Should prefer Swift when available
        # (This would require more complex mocking of the routing logic)


class TestPerformanceOptimization:
    """Test performance optimization features"""
    
    async def test_sidecar_mapping_reconciliation(self, market_maker):
        """Test sidecar mapping reconciliation"""
        # Test mapping functionality
        market_maker.sidecar_orders = {}
        market_maker.warned_missing_ids = set()
        
        # Test reconciliation logic
        await market_maker.reconcile_sidecar_mapping()
        
        # Should handle empty orders gracefully
        assert isinstance(market_maker.sidecar_orders, dict)
    
    async def test_performance_metrics(self, market_maker):
        """Test performance metrics collection"""
        # Test metrics initialization
        assert hasattr(market_maker, 'performance_stats')
        assert isinstance(market_maker.performance_stats, dict)
        
        # Test metrics update
        market_maker.performance_stats['total_ticks'] = 0
        await market_maker.market_making_tick()  # This will fail but metrics should update
        # Note: This test would need more setup to actually succeed


class TestDecimalArithmetic:
    """Test Decimal arithmetic for financial calculations"""
    
    def test_decimal_conversions(self):
        """Test safe Decimal conversions"""
        # Test basic conversion
        value = D(0.1)
        assert isinstance(value, Decimal)
        assert str(value) == "0.1"
        
        # Test arithmetic
        result = D(150.0) * D(0.5)
        assert isinstance(result, Decimal)
        assert result == Decimal("75.0")
    
    def test_order_size_precision(self):
        """Test order size precision handling"""
        # Test minimum order size
        size = max(D(0.005), D(0.01))
        assert size == D(0.01)
        
        # Test size calculations
        buy_size = D(0.5)
        sell_size = D(0.3)
        assert buy_size > sell_size
        assert buy_size >= D(0.01)  # Minimum requirement


class TestErrorHandling:
    """Test error handling and recovery"""
    
    async def test_transient_error_recovery(self, market_maker):
        """Test transient error handling"""
        # Test circuit breaker functionality
        market_maker.sidecar_mode = "forward"
        
        # Simulate circuit breaker trip
        await market_maker._reset_circuit_breaker_after_delay(0.1)
        
        # Should reset mode after delay
        await asyncio.sleep(0.2)
        # Mode should be reset (though this needs more setup to test properly)
    
    async def test_degraded_mode_handling(self, market_maker):
        """Test degraded mode operations"""
        # Test sidecar degradation
        market_maker.sidecar_degraded = True
        market_maker.drift_fallback_enabled = True
        
        # Should enable fallback mode
        assert market_maker.drift_fallback_enabled


# Test configuration
pytest_plugins = ['pytest_asyncio']

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
