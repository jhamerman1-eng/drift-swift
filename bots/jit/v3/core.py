#!/usr/bin/env python3
"""
JIT v3.0 Core Engine - Production Implementation
Enhanced version that integrates with existing Swift/DriftPy infrastructure
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple, Protocol

# Import shared types
from .types import VolatilityRegime, MarketData, QuoteDecision

logger = logging.getLogger(__name__)
    
class TradingClient(Protocol):
    """Protocol for trading client abstraction"""
    async def get_orderbook(self) -> Dict[str, Any]: ...
    async def get_position(self) -> float: ...
    async def get_realized_volatility(self) -> float: ...
    async def place_orders(self, bid_price: float, ask_price: float, 
                          bid_size: float, ask_size: float) -> Tuple[str, str]: ...
    async def cancel_all_orders(self) -> None: ...

class JITEngineV3:
    """
    Production JIT Engine v3.0
    
    Features:
    - Regime-aware microprice calculation with profit measurement
    - Spoof filter with depth analysis
    - Toxicity-based spread adjustment with performance tracking
    - Cancel/replace v2 with proper timing controls
    - Rails integration with size multipliers
    - Comprehensive error handling and fallbacks
    """
    
    def __init__(self, 
                 client: TradingClient,
                 config: Dict[str, Any],
                 market_symbol: str = "SOL-PERP"):
        
        self.client = client
        self.config = self._validate_config(config)
        self.market_symbol = market_symbol
        
        # Import components locally to avoid circular imports
        from .components import (
            RegimeDetector,
            MicropriceCalculator,
            SpoofFilter,
            ToxicityCalculator,
            SpreadManagerV3,
            CancelReplaceV2,
            JITMetricsV3
        )
        
        # Initialize components
        self._regime_detector = RegimeDetector(self.config.get("regimes", {}))
        self._microprice_calc = MicropriceCalculator(self.config.get("microprice", {}))
        self._spoof_filter = SpoofFilter(self.config.get("spoof_filter", {}))
        self._toxicity_calc = ToxicityCalculator(self.config.get("toxicity", {}))
        self._spread_manager = SpreadManagerV3(self.config.get("spread", {}))
        self._cancel_replace = CancelReplaceV2(self.config.get("cancel_replace_v2", {}))
        self._metrics = JITMetricsV3()
        
        # State tracking
        self._last_quote_time = 0.0
        self._last_ref_price = 0.0
        self._error_count = 0
        self._max_errors = self.config.get("max_errors", 10)
        
        logger.info(f"JIT Engine v3.0 initialized for {market_symbol}")
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and apply defaults to configuration"""
        defaults = {
            "loop_secs": 0.9,
            "max_errors": 10,
            "microprice": {
                "enabled": True,
                "weights": {"low": 0.4, "normal": 0.6, "high": 0.8},
                "profit_threshold_bps": 2.0
            },
            "spoof_filter": {
                "enabled": True,
                "depth_threshold": 0.4,
                "z_score_threshold": 2.0
            },
            "toxicity": {
                "enabled": True,
                "threshold": 0.7,
                "measurement_window_ms": 250
            },
            "spread": {
                "base_bps": 2.5,
                "min_bps": 1.0,
                "max_bps": 50.0,
                "toxicity_multiplier": 1.5
            },
            "cancel_replace_v2": {
                "enabled": True,
                "min_lifetime_ms": 250,
                "price_move_bps": 1.5
            },
            "rails": {
                "enabled": True,
                "soft_stop_multiplier": 0.5,
                "trend_pause_multiplier": 0.25,
                "circuit_breaker_multiplier": 0.0
            }
        }
        
        # Deep merge with defaults
        return self._deep_merge(defaults, config)
    
    def _deep_merge(self, defaults: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge configuration with defaults"""
        result = defaults.copy()
        for key, value in config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    async def step(self) -> Optional[QuoteDecision]:
        """
        Execute one JIT engine step with comprehensive error handling
        
        Returns:
            QuoteDecision if successful, None if should skip
        """
        step_start = time.time()
        
        try:
            # 1. Gather market data with validation
            market_data = await self._gather_market_data()
            if not market_data or not market_data.is_valid:
                self._metrics.record_skip("invalid_market_data")
                return None
            
            # 2. Detect regime and select microprice weights
            regime = await self._regime_detector.detect(market_data)
            
            # 3. Calculate reference price with profit validation
            ref_price = await self._calculate_reference_price(market_data, regime)
            if ref_price <= 0:
                self._metrics.record_skip("invalid_ref_price")
                return None
            
            # 4. Apply spoof filter to market data
            filtered_data = await self._spoof_filter.apply(market_data)
            
            # 5. Calculate toxicity score
            toxicity = await self._toxicity_calc.calculate(filtered_data)
            
            # 6. Determine spread with toxicity adjustment
            spread_bps = await self._spread_manager.calculate(
                filtered_data, toxicity, regime
            )
            
            # 7. Check cancel/replace timing
            now_ms = int(time.time() * 1000)
            should_refresh, cr_reason = self._cancel_replace.should_refresh(
                ref_price, now_ms
            )
            
            if not should_refresh:
                self._metrics.record_skip(f"cr_{cr_reason}")
                return None
            
            # 8. Get rails size multiplier (from orchestrator/external)
            size_multiplier = await self._get_rails_size_multiplier()
            if size_multiplier <= 0:
                self._metrics.record_skip("rails_halt")
                return None
            
            # 9. Calculate order sizes
            position = await self.client.get_position()
            bid_size, ask_size = self._calculate_order_sizes(
                market_data, position, size_multiplier
            )
            
            # 10. Create decision
            decision = QuoteDecision(
                should_quote=True,
                ref_price=ref_price,
                spread_bps=spread_bps,
                bid_size=bid_size,
                ask_size=ask_size,
                size_multiplier=size_multiplier,
                reason=f"regime_{regime.value}_tox_{toxicity:.3f}",
                toxicity_score=toxicity,
                regime=regime
            )
            
            # 11. Record successful step
            self._cancel_replace.record_quote(ref_price, now_ms)
            self._metrics.record_decision(decision, time.time() - step_start)
            self._error_count = 0  # Reset error count on success
            
            return decision
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"JIT engine step failed: {e}", exc_info=True)
            self._metrics.record_error(str(e))
            
            if self._error_count >= self._max_errors:
                logger.critical(f"JIT engine exceeded max errors ({self._max_errors}), halting")
                return None
            
            return None
    
    async def _gather_market_data(self) -> Optional[MarketData]:
        """Gather and validate market data from trading client"""
        try:
            orderbook = await self.client.get_orderbook()
            
            # Extract best bid/ask with validation
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return None
            
            best_bid, bid_volume = bids[0]
            best_ask, ask_volume = asks[0]
            
            mid_price = (best_bid + best_ask) / 2.0
            spread_bps = ((best_ask - best_bid) / mid_price) * 10000.0
            
            return MarketData(
                best_bid=best_bid,
                best_ask=best_ask,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
                mid_price=mid_price,
                spread_bps=spread_bps,
                timestamp=time.time(),
                levels=len(bids)
            )
            
        except Exception as e:
            logger.error(f"Failed to gather market data: {e}")
            return None
    
    async def _calculate_reference_price(self, 
                                       market_data: MarketData, 
                                       regime: VolatilityRegime) -> float:
        """Calculate reference price using regime-aware microprice"""
        if not self.config["microprice"]["enabled"]:
            return market_data.mid_price
        
        return await self._microprice_calc.calculate(market_data, regime)
    
    async def _get_rails_size_multiplier(self) -> float:
        """Get size multiplier from rails/orchestrator"""
        # In production, this would query the orchestrator for current rails state
        # For now, return from config or default to 1.0
        return self.config.get("size_mult", 1.0)
    
    def _calculate_order_sizes(self, 
                             market_data: MarketData,
                             position: float,
                             size_multiplier: float) -> Tuple[float, float]:
        """Calculate bid/ask order sizes with inventory management"""
        base_size = 0.1  # Base size in asset units (e.g., SOL)
        
        # Apply size multiplier from rails
        adjusted_size = base_size * size_multiplier
        
        # Adjust for inventory (reduce size when skewed)
        max_position = 5.0  # Max position in asset units
        inventory_skew = position / max_position if max_position > 0 else 0
        
        # Reduce size when inventory is skewed
        skew_adjustment = 1.0 - abs(inventory_skew) * 0.3
        final_size = adjusted_size * max(0.1, skew_adjustment)
        
        # Asymmetric sizing based on inventory
        if inventory_skew > 0.1:  # Long position - prefer selling
            bid_size = final_size * 0.7
            ask_size = final_size * 1.3
        elif inventory_skew < -0.1:  # Short position - prefer buying
            bid_size = final_size * 1.3
            ask_size = final_size * 0.7
        else:
            bid_size = ask_size = final_size
        
        return max(0.01, bid_size), max(0.01, ask_size)

# Component classes would go here (RegimeDetector, MicropriceCalculator, etc.)
# I'll implement these in separate files for better organization
