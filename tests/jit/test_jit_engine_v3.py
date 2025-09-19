#!/usr/bin/env python3
"""
Comprehensive unit tests for JIT Engine v3.0
Tests all components with normal flow, fallback scenarios, and edge cases
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock

# Import test targets
import sys
import os
# Add the bots directory to Python path for imports
bots_path = os.path.join(os.path.dirname(__file__), '..', 'bots')
sys.path.insert(0, bots_path)

from jit.v3.core import JITEngineV3, MarketData, QuoteDecision, VolatilityRegime
from jit.v3.components import (
    RegimeDetector, MicropriceCalculator, SpoofFilter,
    ToxicityCalculator, SpreadManagerV3, CancelReplaceV2
)
from jit.v3.integration import JITEngineAdapter

class TestMarketData:
    """Test MarketData validation and properties"""
    
    def test_valid_market_data(self):
        """Test valid market data creation and validation"""
        data = MarketData(
            best_bid=100.0,
            best_ask=100.5,
            bid_volume=10.0,
            ask_volume=15.0,
            mid_price=100.25,
            spread_bps=50.0,
            timestamp=time.time()
        )
        
        assert data.is_valid
        assert data.mid_price == 100.25
        assert data.spread_bps == 50.0
    
    def test_invalid_market_data_crossed_book(self):
        """Test detection of crossed orderbook"""
        data = MarketData(
            best_bid=100.5,  # Bid higher than ask
            best_ask=100.0,
            bid_volume=10.0,
            ask_volume=15.0,
            mid_price=100.25,
            spread_bps=50.0,
            timestamp=time.time()
        )
        
        assert not data.is_valid
    
    def test_invalid_market_data_zero_volume(self):
        """Test detection of zero volume"""
        data = MarketData(
            best_bid=100.0,
            best_ask=100.5,
            bid_volume=0.0,  # Zero volume
            ask_volume=15.0,
            mid_price=100.25,
            spread_bps=50.0,
            timestamp=time.time()
        )
        
        assert not data.is_valid

class TestRegimeDetector:
    """Test volatility regime detection"""
    
    def test_regime_detection_normal(self):
        """Test normal volatility regime detection"""
        config = {
            "thresholds": {"low_vol": 0.001, "high_vol": 0.005}
        }
        detector = RegimeDetector(config)
        
        # Create market data with normal volatility
        market_data = MarketData(
            best_bid=100.0, best_ask=100.3, bid_volume=10.0, ask_volume=10.0,
            mid_price=100.15, spread_bps=30.0, timestamp=time.time()
        )
        
        regime = asyncio.run(detector.detect(market_data))
        assert regime == VolatilityRegime.NORMAL
    
    def test_regime_detection_high_vol(self):
        """Test high volatility regime detection"""
        config = {
            "thresholds": {"low_vol": 0.001, "high_vol": 0.005}
        }
        detector = RegimeDetector(config)
        
        # Add several high volatility readings
        for _ in range(10):
            market_data = MarketData(
                best_bid=100.0, best_ask=101.0, bid_volume=10.0, ask_volume=10.0,
                mid_price=100.5, spread_bps=1000.0, timestamp=time.time()  # High spread
            )
            asyncio.run(detector.detect(market_data))
        
        # Should now detect high volatility
        final_regime = asyncio.run(detector.detect(market_data))
        assert final_regime == VolatilityRegime.HIGH

class TestMicropriceCalculator:
    """Test microprice calculation with profit validation"""
    
    def test_microprice_calculation(self):
        """Test basic microprice calculation"""
        config = {
            "weights": {"low": 0.4, "normal": 0.6, "high": 0.8},
            "profit_threshold_bps": 2.0
        }
        calc = MicropriceCalculator(config)
        
        market_data = MarketData(
            best_bid=100.0, best_ask=100.5, bid_volume=20.0, ask_volume=10.0,
            mid_price=100.25, spread_bps=50.0, timestamp=time.time()
        )
        
        # Should calculate weighted microprice
        # microprice = (20 * 100.5 + 10 * 100.0) / 30 = 100.33
        # final = 0.6 * 100.33 + 0.4 * 100.25 = 100.298
        result = asyncio.run(calc.calculate(market_data, VolatilityRegime.NORMAL))
        
        assert result > 100.25  # Should be closer to ask due to bid volume > ask volume
        assert result < 100.5
    
    def test_microprice_profit_threshold(self):
        """Test profit threshold enforcement"""
        config = {
            "weights": {"normal": 0.6},
            "profit_threshold_bps": 100.0  # Very high threshold
        }
        calc = MicropriceCalculator(config)
        
        market_data = MarketData(
            best_bid=100.0, best_ask=100.1, bid_volume=10.0, ask_volume=10.0,
            mid_price=100.05, spread_bps=10.0, timestamp=time.time()
        )
        
        # Should fall back to mid price due to high profit threshold
        result = asyncio.run(calc.calculate(market_data, VolatilityRegime.NORMAL))
        assert result == market_data.mid_price

class TestSpoofFilter:
    """Test spoof filter functionality"""
    
    def test_spoof_filter_disabled(self):
        """Test spoof filter when disabled"""
        config = {"enabled": False}
        filter_obj = SpoofFilter(config)
        
        market_data = MarketData(
            best_bid=100.0, best_ask=100.5, bid_volume=0.1, ask_volume=0.1,  # Very small volumes
            mid_price=100.25, spread_bps=50.0, timestamp=time.time()
        )
        
        result = asyncio.run(filter_obj.apply(market_data))
        assert result == market_data  # Should be unchanged
    
    def test_spoof_filter_adjustment(self):
        """Test spoof filter price adjustment"""
        config = {
            "enabled": True,
            "depth_threshold": 0.4
        }
        filter_obj = SpoofFilter(config)
        
        market_data = MarketData(
            best_bid=100.0, best_ask=100.5, bid_volume=1.0, ask_volume=0.1,  # Ask volume very small
            mid_price=100.25, spread_bps=50.0, timestamp=time.time()
        )
        
        result = asyncio.run(filter_obj.apply(market_data))
        
        # Ask should be adjusted higher due to suspected spoof
        assert result.best_ask > market_data.best_ask
        assert result.best_bid == market_data.best_bid  # Bid should be unchanged

class TestToxicityCalculator:
    """Test toxicity score calculation"""
    
    def test_toxicity_calculation_stable(self):
        """Test toxicity calculation with stable spreads"""
        config = {"enabled": True, "measurement_window_ms": 250}
        calc = ToxicityCalculator(config)
        
        # Add several stable spread readings
        for _ in range(5):
            market_data = MarketData(
                best_bid=100.0, best_ask=100.5, bid_volume=10.0, ask_volume=10.0,
                mid_price=100.25, spread_bps=50.0, timestamp=time.time()
            )
            toxicity = asyncio.run(calc.calculate(market_data))
        
        # Should have low toxicity for stable spreads
        assert toxicity < 0.3
    
    def test_toxicity_calculation_volatile(self):
        """Test toxicity calculation with volatile spreads"""
        config = {"enabled": True, "measurement_window_ms": 250}
        calc = ToxicityCalculator(config)
        
        # Add volatile spread readings
        spreads = [50.0, 100.0, 25.0, 150.0, 75.0]
        for spread in spreads:
            market_data = MarketData(
                best_bid=100.0, best_ask=100.0 + spread/10000*100, 
                bid_volume=10.0, ask_volume=10.0,
                mid_price=100.0 + spread/20000*100, spread_bps=spread, 
                timestamp=time.time()
            )
            toxicity = asyncio.run(calc.calculate(market_data))
        
        # Should have higher toxicity for volatile spreads
        assert toxicity > 0.3

class TestSpreadManagerV3:
    """Test enhanced spread management"""
    
    def test_spread_calculation_normal(self):
        """Test normal spread calculation"""
        config = {
            "base_bps": 5.0,
            "min_bps": 2.0, 
            "max_bps": 20.0,
            "toxicity_multiplier": 1.5,
            "toxicity_threshold": 0.7
        }
        manager = SpreadManagerV3(config)
        
        market_data = MarketData(
            best_bid=100.0, best_ask=100.2, bid_volume=10.0, ask_volume=10.0,
            mid_price=100.1, spread_bps=20.0, timestamp=time.time()
        )
        
        result = asyncio.run(manager.calculate(market_data, 0.3, VolatilityRegime.NORMAL))
        assert result >= config["min_bps"]
        assert result <= config["max_bps"]
    
    def test_spread_toxicity_adjustment(self):
        """Test spread adjustment for high toxicity"""
        config = {
            "base_bps": 5.0,
            "toxicity_multiplier": 1.5,
            "toxicity_threshold": 0.7
        }
        manager = SpreadManagerV3(config)
        
        market_data = MarketData(
            best_bid=100.0, best_ask=100.2, bid_volume=10.0, ask_volume=10.0,
            mid_price=100.1, spread_bps=20.0, timestamp=time.time()
        )
        
        # High toxicity should increase spread
        high_tox_spread = asyncio.run(manager.calculate(market_data, 0.9, VolatilityRegime.NORMAL))
        low_tox_spread = asyncio.run(manager.calculate(market_data, 0.3, VolatilityRegime.NORMAL))
        
        assert high_tox_spread > low_tox_spread

class TestCancelReplaceV2:
    """Test enhanced cancel/replace logic"""
    
    def test_cancel_replace_init(self):
        """Test initial quote should always be placed"""
        config = {"enabled": True, "min_lifetime_ms": 250, "price_move_bps": 1.5}
        cr = CancelReplaceV2(config)
        
        should_refresh, reason = cr.should_refresh(100.0, int(time.time() * 1000))
        assert should_refresh
        assert reason == "init"
    
    def test_cancel_replace_min_lifetime(self):
        """Test minimum lifetime enforcement"""
        config = {"enabled": True, "min_lifetime_ms": 1000, "price_move_bps": 1.5}
        cr = CancelReplaceV2(config)
        
        now_ms = int(time.time() * 1000)
        cr.record_quote(100.0, now_ms)
        
        # Immediate check should be blocked
        should_refresh, reason = cr.should_refresh(100.0, now_ms + 100)
        assert not should_refresh
        assert "min_lifetime" in reason
    
    def test_cancel_replace_price_movement(self):
        """Test price movement threshold"""
        config = {"enabled": True, "min_lifetime_ms": 100, "price_move_bps": 10.0}
        cr = CancelReplaceV2(config)
        
        now_ms = int(time.time() * 1000)
        cr.record_quote(100.0, now_ms)
        
        # Small price move should not trigger refresh
        should_refresh, reason = cr.should_refresh(100.05, now_ms + 200)
        assert not should_refresh
        
        # Large price move should trigger refresh  
        should_refresh, reason = cr.should_refresh(100.15, now_ms + 200)  # 15 bps move
        assert should_refresh
        assert "price_move" in reason

class TestJITEngineV3:
    """Test complete JIT engine integration"""
    
    @pytest.fixture
    def mock_trading_client(self):
        """Create mock trading client"""
        client = AsyncMock()
        client.get_orderbook.return_value = {
            'bids': [(100.0, 10.0), (99.9, 5.0)],
            'asks': [(100.5, 8.0), (100.6, 12.0)],
            'timestamp': time.time()
        }
        client.get_position.return_value = 0.5  # Small long position
        client.get_realized_volatility.return_value = 0.002
        return client
    
    @pytest.fixture
    def jit_config(self):
        """Create test JIT configuration"""
        return {
            "loop_secs": 0.9,
            "microprice": {"enabled": True, "profit_threshold_bps": 1.0},
            "spoof_filter": {"enabled": True},
            "toxicity": {"enabled": True},
            "spread": {"base_bps": 5.0, "min_bps": 2.0, "max_bps": 20.0},
            "cancel_replace_v2": {"enabled": True, "min_lifetime_ms": 100},
            "size_mult": 1.0
        }
    
    def test_jit_engine_initialization(self, mock_trading_client, jit_config):
        """Test JIT engine initialization"""
        engine = JITEngineV3(mock_trading_client, jit_config, "SOL-PERP")
        
        assert engine.market_symbol == "SOL-PERP"
        assert engine._max_errors == 10
        assert engine.config["spread"]["base_bps"] == 5.0
    
    @pytest.mark.asyncio
    async def test_jit_engine_normal_step(self, mock_trading_client, jit_config):
        """Test normal JIT engine step"""
        engine = JITEngineV3(mock_trading_client, jit_config, "SOL-PERP")
        
        decision = await engine.step()
        
        assert decision is not None
        assert decision.should_quote
        assert decision.ref_price > 0
        assert decision.spread_bps > 0
        assert decision.bid_size > 0
        assert decision.ask_size > 0
    
    @pytest.mark.asyncio
    async def test_jit_engine_invalid_market_data(self, mock_trading_client, jit_config):
        """Test JIT engine with invalid market data"""
        # Mock invalid orderbook
        mock_trading_client.get_orderbook.return_value = {
            'bids': [],  # Empty bids
            'asks': [(100.5, 8.0)],
            'timestamp': time.time()
        }
        
        engine = JITEngineV3(mock_trading_client, jit_config, "SOL-PERP")
        decision = await engine.step()
        
        assert decision is None  # Should skip due to invalid data
    
    @pytest.mark.asyncio
    async def test_jit_engine_error_handling(self, mock_trading_client, jit_config):
        """Test JIT engine error handling"""
        # Mock client that throws errors
        mock_trading_client.get_orderbook.side_effect = Exception("Network error")
        
        engine = JITEngineV3(mock_trading_client, jit_config, "SOL-PERP")
        
        # Should handle errors gracefully
        decision = await engine.step()
        assert decision is None
        assert engine._error_count == 1

class TestJITEngineAdapter:
    """Test JIT engine adapter integration"""
    
    @pytest.fixture
    def mock_jit_engine(self):
        """Create mock JIT engine"""
        engine = AsyncMock()
        engine._metrics = Mock()
        engine._metrics.get_stats.return_value = {
            'decisions_total': 5,
            'skips_total': 2,
            'errors_total': 0
        }
        return engine
    
    @pytest.fixture
    def mock_trading_client(self):
        """Create mock trading client"""
        client = AsyncMock()
        client.place_orders.return_value = ("bid_123", "ask_456")
        return client
    
    @pytest.mark.asyncio
    async def test_adapter_normal_tick(self, mock_jit_engine, mock_trading_client):
        """Test normal adapter tick"""
        # Mock successful decision
        decision = QuoteDecision(
            should_quote=True,
            ref_price=100.25,
            spread_bps=10.0,
            bid_size=0.1,
            ask_size=0.1,
            size_multiplier=1.0,
            reason="test",
            toxicity_score=0.3,
            regime=VolatilityRegime.NORMAL
        )
        mock_jit_engine.step.return_value = decision
        
        adapter = JITEngineAdapter(mock_jit_engine, mock_trading_client, {})
        result = await adapter.tick()
        
        assert result['action'] == 'quote'
        assert result['bid_id'] == "bid_123"
        assert result['ask_id'] == "ask_456"
        assert result['ref_price'] == 100.25
        assert result['spread_bps'] == 10.0
    
    @pytest.mark.asyncio
    async def test_adapter_skip_tick(self, mock_jit_engine, mock_trading_client):
        """Test adapter skip decision"""
        mock_jit_engine.step.return_value = None
        
        adapter = JITEngineAdapter(mock_jit_engine, mock_trading_client, {})
        result = await adapter.tick()
        
        assert result['action'] == 'skip'
        assert result['reason'] == 'no_decision'
    
    def test_adapter_stats(self, mock_jit_engine, mock_trading_client):
        """Test adapter stats collection"""
        adapter = JITEngineAdapter(mock_jit_engine, mock_trading_client, {})
        stats = adapter.get_stats()
        
        assert 'jit_engine' in stats
        assert 'adapter_version' in stats
        assert stats['adapter_version'] == '3.0.0'

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
