"""
Unit tests for Ultimate Hedge Bot Effective Cost Router
Tests the fixed non-linear EC calculation with proper size impact.
"""

import pytest
import math
from ultimate_hedge_bot.core.effective_cost_router import (
    EffectiveCostRouter, RoutingCandidate, RoutingResult
)


class TestEffectiveCostRouter:
    """Comprehensive tests for the fixed effective cost router."""

    def setup_method(self):
        """Setup test fixtures."""
        self.config = {
            'hedge': {'max_inventory_usd': 1500.0},
            'rpc': {'timeout_seconds': 30}
        }
        self.router = EffectiveCostRouter(self.config)

    def test_slippage_calculation_buy_order(self):
        """Test slippage calculation for buy orders."""
        # Sample orderbook
        orderbook = {
            'bids': [[100.0, 10.0], [99.5, 15.0], [99.0, 20.0]],
            'asks': [[100.5, 12.0], [101.0, 18.0], [101.5, 25.0]]
        }

        # Buy 5 units
        qty = 5.0
        slippage = self.router._calculate_slippage_impact(orderbook, 'buy', qty)

        # Expected: walk the ask side
        # 5 units at 100.5 = 502.5 total cost, avg = 100.5, slippage = 0.5/100.5 = 0.00498
        expected_slippage = (100.5 - 100.5) / 100.5  # No slippage in this simple case
        assert abs(slippage - expected_slippage) < 0.0001

    def test_slippage_calculation_sell_order(self):
        """Test slippage calculation for sell orders."""
        orderbook = {
            'bids': [[100.0, 10.0], [99.5, 15.0], [99.0, 20.0]],
            'asks': [[100.5, 12.0], [101.0, 18.0], [101.5, 25.0]]
        }

        # Sell 5 units
        qty = 5.0
        slippage = self.router._calculate_slippage_impact(orderbook, 'sell', qty)

        # Expected: walk the bid side
        # 5 units at 100.0 = 500.0 total cost, avg = 100.0, slippage = (100.0 - 100.0) / 100.0 = 0
        expected_slippage = 0.0
        assert abs(slippage - expected_slippage) < 0.0001

    def test_slippage_calculation_partial_fill(self):
        """Test slippage calculation with partial fills across multiple levels."""
        orderbook = {
            'bids': [[100.0, 10.0], [99.5, 15.0], [99.0, 20.0]],
            'asks': [[100.5, 12.0], [101.0, 18.0], [101.5, 25.0]]
        }

        # Buy 20 units (more than first level)
        qty = 20.0
        slippage = self.router._calculate_slippage_impact(orderbook, 'buy', qty)

        # Expected calculation:
        # Level 1: 12 units @ 100.5 = 1206.0
        # Level 2: 8 units @ 101.0 = 808.0
        # Total: 20 units, 2014.0 cost, avg = 100.7
        # Slippage = (100.7 - 100.5) / 100.5 = 0.00199
        expected_avg = (12 * 100.5 + 8 * 101.0) / 20
        expected_slippage = (expected_avg - 100.5) / 100.5

        assert abs(slippage - expected_slippage) < 0.0001
        assert slippage > 0  # Should have positive slippage

    def test_non_linear_size_impact(self):
        """Test the non-linear size impact calculation."""
        # Sample orderbook
        orderbook = {
            'bids': [[100.0, 100.0]],  # Deep liquidity
            'asks': [[100.5, 100.0]]
        }

        # Test different order sizes
        sizes = [1.0, 10.0, 100.0, 1000.0]
        results = []

        for size in sizes:
            cost = self.router._calculate_slippage_impact(orderbook, 'buy', size)
            results.append(cost)

        # For small sizes, impact should be minimal (linear)
        # For large sizes, impact should increase non-linearly
        assert results[0] < results[1]  # 1 < 10
        assert results[1] < results[2]  # 10 < 100
        assert results[2] < results[3]  # 100 < 1000

        # Test that the impact grows faster than linearly
        linear_growth = results[3] / results[0]  # 1000x size
        actual_growth = (results[3] - results[0]) / results[0]

        # The non-linear formula should show super-linear growth for large sizes
        assert actual_growth > linear_growth * 0.1  # At least 10% more than linear

    def test_size_multiplier_calculation(self):
        """Test the size multiplier calculation."""
        # Test small order
        small_multiplier = self.router._calculate_size_multiplier(100, 'drift')
        assert small_multiplier > 1.0  # Should be greater than 1

        # Test large order
        large_multiplier = self.router._calculate_size_multiplier(10000, 'drift')
        assert large_multiplier > small_multiplier  # Larger orders have bigger impact

        # Test that it's using square root relationship
        expected_large = math.sqrt(1 + 10000 / 50000000)  # Drift avg volume
        assert abs(large_multiplier - expected_large) < 0.01

    def test_venue_specific_configurations(self):
        """Test venue-specific configurations and fees."""
        # Test Drift configuration
        drift_config = self.router.venue_configs['drift']
        assert drift_config['leverage'] == 10
        assert drift_config['maker_fee_bps'] == 0
        assert drift_config['taker_fee_bps'] == 5

        # Test Binance configuration
        binance_config = self.router.venue_configs['binance']
        assert binance_config['leverage'] == 20
        assert binance_config['maker_fee_bps'] == -2.5  # Negative for rebate
        assert binance_config['taker_fee_bps'] == 7.5

        # Test Bybit configuration
        bybit_config = self.router.venue_configs['bybit']
        assert bybit_config['leverage'] == 100
        assert bybit_config['maker_fee_bps'] == -2
        assert bybit_config['taker_fee_bps'] == 6

    def test_fee_calculations(self):
        """Test venue-specific fee calculations."""
        # Test Drift fees
        drift_maker = self.router._get_venue_fees('drift', 'maker')
        drift_taker = self.router._get_venue_fees('drift', 'taker')
        assert drift_maker == 0
        assert drift_taker == 5

        # Test Binance fees (with rebates)
        binance_maker = self.router._get_venue_fees('binance', 'maker')
        binance_taker = self.router._get_venue_fees('binance', 'taker')
        assert binance_maker == -2.5  # Rebate
        assert binance_taker == 7.5

    @pytest.mark.asyncio
    async def test_effective_cost_calculation_maker(self):
        """Test complete effective cost calculation for maker orders."""
        orderbook = {
            'bids': [[100.0, 100.0]],
            'asks': [[100.5, 100.0]]
        }

        # Small maker order
        cost = await self.router.calculate_effective_cost(
            orderbook, 'buy', 10.0, 'drift', 'maker'
        )

        # For maker order with small size, cost should be minimal
        # EC = slippage + fees, slippage should be ~0, fees = 0 for Drift maker
        assert cost >= 0.0
        assert cost < 0.001  # Less than 0.1% for small maker order

    @pytest.mark.asyncio
    async def test_effective_cost_calculation_taker(self):
        """Test complete effective cost calculation for taker orders."""
        orderbook = {
            'bids': [[100.0, 100.0]],
            'asks': [[100.5, 100.0]]
        }

        # Small taker order
        cost = await self.router.calculate_effective_cost(
            orderbook, 'buy', 10.0, 'drift', 'taker'
        )

        # For taker order, should include taker fees
        expected_fee_component = 5 / 10000  # 5 bps taker fee
        assert cost >= expected_fee_component

    @pytest.mark.asyncio
    async def test_effective_cost_size_impact(self):
        """Test that effective cost properly accounts for order size impact."""
        orderbook = {
            'bids': [[100.0, 50.0]],  # Limited liquidity
            'asks': [[100.5, 50.0]]
        }

        # Small order
        small_cost = await self.router.calculate_effective_cost(
            orderbook, 'buy', 1.0, 'drift', 'taker'
        )

        # Large order (exceeds available liquidity)
        large_cost = await self.router.calculate_effective_cost(
            orderbook, 'buy', 100.0, 'drift', 'taker'
        )

        # Large order should have significantly higher cost
        assert large_cost > small_cost
        assert large_cost / small_cost > 2.0  # At least 2x more expensive

    @pytest.mark.asyncio
    async def test_routing_comparison(self):
        """Test routing comparison between venues."""
        # Create mock orderbook data
        orderbook_data = {
            'drift': {
                'bids': [[100.0, 100.0]],
                'asks': [[100.5, 100.0]]
            },
            'binance': {
                'bids': [[100.0, 100.0]],
                'asks': [[100.5, 100.0]]
            }
        }

        # Test routing for small order
        result = await self.router.find_best_routing(
            orderbook_data, 'buy', 10.0, 0.5
        )

        # Should select a venue
        assert result.best_venue in ['drift', 'binance']
        assert result.effective_cost >= 0.0
        assert len(result.routing_candidates) == 2
        assert result.routing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_maker_vs_taker_selection(self):
        """Test automatic selection between maker and taker."""
        # Deep orderbook favoring maker
        deep_orderbook = {
            'bids': [[100.0, 1000.0]],  # Very deep
            'asks': [[100.01, 1000.0]]  # Very tight spread
        }

        # Small order should prefer maker
        cost_maker = await self.router.calculate_effective_cost(
            deep_orderbook, 'buy', 1.0, 'drift', 'maker'
        )
        cost_taker = await self.router.calculate_effective_cost(
            deep_orderbook, 'buy', 1.0, 'drift', 'taker'
        )

        # Maker should be cheaper (Drift maker fee = 0, taker fee = 5bps)
        assert cost_maker < cost_taker

    def test_confidence_scoring(self):
        """Test routing confidence scoring."""
        # Deep orderbook = high confidence
        deep_orderbook = {
            'bids': [[100.0, 100.0], [99.5, 100.0]],
            'asks': [[100.5, 100.0], [101.0, 100.0]]
        }

        confidence = self.router._calculate_routing_confidence(deep_orderbook, 10.0, 'drift')
        assert confidence > 0.5  # Should be reasonably high

        # Shallow orderbook = low confidence
        shallow_orderbook = {
            'bids': [[100.0, 1.0]],  # Very shallow
            'asks': [[100.5, 1.0]]
        }

        confidence_shallow = self.router._calculate_routing_confidence(shallow_orderbook, 10.0, 'drift')
        assert confidence_shallow < confidence  # Should be lower than deep orderbook

    def test_fill_time_estimation(self):
        """Test fill time estimation."""
        # Small order should be fast
        fast_time = self.router._estimate_fill_time('drift', 10.0, 'maker')
        assert fast_time < 100  # Less than 100ms

        # Large order should be slower
        slow_time = self.router._estimate_fill_time('drift', 1000.0, 'taker')
        assert slow_time > fast_time  # Should be slower

    async def test_urgency_adjustment(self):
        """Test urgency score adjustments."""
        orderbook_data = {
            'drift': {
                'bids': [[100.0, 100.0]],
                'asks': [[100.5, 100.0]]
            }
        }

        # Normal urgency
        result_normal = await self.router.find_best_routing(
            orderbook_data, 'buy', 10.0, 0.0  # No urgency
        )

        # High urgency
        result_urgent = await self.router.find_best_routing(
            orderbook_data, 'buy', 10.0, 0.8  # High urgency
        )

        # High urgency should have lower effective cost (discount applied)
        assert result_urgent.effective_cost <= result_normal.effective_cost

    def test_invalid_orderbook_handling(self):
        """Test handling of invalid or missing orderbook data."""
        # Empty orderbook
        empty_orderbook = {'bids': [], 'asks': []}

        cost = self.router._calculate_slippage_impact(empty_orderbook, 'buy', 10.0)
        assert cost == 0.005  # Should return default value

        # Missing keys
        incomplete_orderbook = {'bids': [[100.0, 10.0]]}  # Missing asks

        cost = self.router._calculate_slippage_impact(incomplete_orderbook, 'buy', 10.0)
        assert cost == 0.005  # Should return default value

    def test_extreme_values_handling(self):
        """Test handling of extreme values."""
        # Zero quantity
        cost = self.router._calculate_slippage_impact(
            {'bids': [[100.0, 10.0]], 'asks': [[100.5, 10.0]]},
            'buy', 0.0
        )
        assert cost == 0.0

        # Very large quantity
        large_orderbook = {
            'bids': [[100.0, 1000000.0]],  # Very deep liquidity
            'asks': [[100.5, 1000000.0]]
        }

        cost = self.router._calculate_slippage_impact(large_orderbook, 'buy', 100000.0)
        assert cost >= 0.0  # Should handle large numbers gracefully

    def test_venue_config_validation(self):
        """Test venue configuration validation."""
        # Valid venue
        assert 'drift' in self.router.venue_configs
        assert 'binance' in self.router.venue_configs

        # Check required fields
        for venue, config in self.router.venue_configs.items():
            required_fields = ['maker_fee_bps', 'taker_fee_bps', 'avg_daily_volume']
            for field in required_fields:
                assert field in config
                assert isinstance(config[field], (int, float))

    def test_routing_stats_access(self):
        """Test access to routing statistics."""
        stats = self.router.get_routing_stats()

        assert 'venue_configs' in stats
        assert 'size_impact_coefficients' in stats
        assert 'supported_venues' in stats

        assert len(stats['supported_venues']) > 0
        assert 'drift' in stats['supported_venues']
