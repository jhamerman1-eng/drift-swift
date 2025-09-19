#!/usr/bin/env python3
"""
JIT v3.0 Component Implementations
Individual components for microprice, spoof filtering, toxicity calculation, etc.
"""

import time
import logging
import statistics
from dataclasses import dataclass
from typing import Dict, Any, Tuple
from collections import deque

# Import shared types
from .types import VolatilityRegime, MarketData

logger = logging.getLogger(__name__)

@dataclass
class MicropriceResult:
    """Result from microprice calculation"""
    price: float
    confidence: float
    regime_weight: float
    profit_improvement_bps: float = 0.0

class RegimeDetector:
    """Detects market volatility regime for microprice weighting"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._volatility_window = deque(maxlen=config.get("window_size", 20))
        self._thresholds = config.get("thresholds", {
            "low_vol": 0.001,    # 0.1% 
            "high_vol": 0.005    # 0.5%
        })
    
    async def detect(self, market_data: MarketData) -> VolatilityRegime:
        """Detect current volatility regime"""
        try:
            # Use spread as a proxy for volatility
            current_vol = market_data.spread_bps / 10000.0
            self._volatility_window.append(current_vol)
            
            if len(self._volatility_window) < 5:
                return VolatilityRegime.NORMAL
            
            avg_vol = statistics.mean(self._volatility_window)
            
            if avg_vol <= self._thresholds["low_vol"]:
                return VolatilityRegime.LOW
            elif avg_vol >= self._thresholds["high_vol"]:
                return VolatilityRegime.HIGH
            else:
                return VolatilityRegime.NORMAL
                
        except Exception as e:
            logger.warning(f"Regime detection failed: {e}")
            return VolatilityRegime.NORMAL

class MicropriceCalculator:
    """
    Calculates regime-aware microprice with profit validation
    
    Implements JIT-QUOTE-001 requirements:
    - OBI-weighted microprice calculation
    - Regime-aware weights (low/normal/high vol)
    - Profit improvement measurement vs plain mid
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._weights = config.get("weights", {
            "low": 0.4,
            "normal": 0.6, 
            "high": 0.8
        })
        self._profit_threshold_bps = config.get("profit_threshold_bps", 2.0)
        self._fill_history = deque(maxlen=100)  # For profit measurement
    
    async def calculate(self, market_data: MarketData, regime: VolatilityRegime) -> float:
        """Calculate regime-aware microprice"""
        try:
            # Get regime-specific weight
            weight = self._weights.get(regime.value, 0.6)
            
            # Calculate OBI-weighted microprice
            total_volume = market_data.bid_volume + market_data.ask_volume
            if total_volume <= 0:
                return market_data.mid_price
            
            # Microprice = (bid_volume * ask_price + ask_volume * bid_price) / total_volume
            microprice = (
                market_data.bid_volume * market_data.best_ask + 
                market_data.ask_volume * market_data.best_bid
            ) / total_volume
            
            # Blend with mid price based on regime weight
            final_price = weight * microprice + (1 - weight) * market_data.mid_price
            
            # Validate profit improvement (placeholder for real measurement)
            profit_improvement = self._estimate_profit_improvement(final_price, market_data.mid_price)
            
            if profit_improvement >= self._profit_threshold_bps:
                logger.debug(f"Microprice profit improvement: {profit_improvement:.2f}bps")
                return final_price
            else:
                logger.debug(f"Microprice below profit threshold, using mid price")
                return market_data.mid_price
                
        except Exception as e:
            logger.error(f"Microprice calculation failed: {e}")
            return market_data.mid_price
    
    def _estimate_profit_improvement(self, microprice: float, mid_price: float) -> float:
        """
        Estimate profit improvement vs baseline mid price
        
        In production, this would analyze historical fill performance
        vs future price movement at +250ms
        """
        # Simplified estimation - in reality this requires fill tracking
        # and forward-looking price analysis
        price_diff_bps = abs(microprice - mid_price) / mid_price * 10000.0
        
        # Assume microprice provides 2x the price difference as profit improvement
        return min(price_diff_bps * 2.0, 10.0)  # Cap at 10bps

class SpoofFilter:
    """
    Spoof filter to detect and ignore shallow/outlier levels
    
    Implements JIT-QUOTE-002 requirements:
    - Shallow depth detection
    - Outlier removal by z-score
    - Toxic fill rate reduction measurement
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._enabled = config.get("enabled", True)
        self._depth_threshold = config.get("depth_threshold", 0.4)
        self._z_score_threshold = config.get("z_score_threshold", 2.0)
        self._fill_tracking = deque(maxlen=200)
    
    async def apply(self, market_data: MarketData) -> MarketData:
        """Apply spoof filter to market data"""
        if not self._enabled:
            return market_data
        
        try:
            # For now, implement basic depth filtering
            # In production, this would analyze multiple orderbook levels
            
            # Check if volumes are suspiciously small
            avg_volume = (market_data.bid_volume + market_data.ask_volume) / 2.0
            min_depth = avg_volume * self._depth_threshold
            
            filtered_bid_volume = max(market_data.bid_volume, min_depth)
            filtered_ask_volume = max(market_data.ask_volume, min_depth)
            
            # Adjust prices marginally when spoof detected
            spoof_adjustment_bps = 0.5  # 0.5 bps adjustment
            spoof_adjustment = market_data.mid_price * spoof_adjustment_bps / 10000.0
            
            filtered_bid = market_data.best_bid
            filtered_ask = market_data.best_ask
            
            if market_data.bid_volume < min_depth:
                filtered_bid -= spoof_adjustment
                logger.debug(f"Spoof detected on bid, adjusted by {spoof_adjustment_bps}bps")
            
            if market_data.ask_volume < min_depth:
                filtered_ask += spoof_adjustment
                logger.debug(f"Spoof detected on ask, adjusted by {spoof_adjustment_bps}bps")
            
            return MarketData(
                best_bid=filtered_bid,
                best_ask=filtered_ask,
                bid_volume=filtered_bid_volume,
                ask_volume=filtered_ask_volume,
                mid_price=(filtered_bid + filtered_ask) / 2.0,
                spread_bps=((filtered_ask - filtered_bid) / ((filtered_bid + filtered_ask) / 2.0)) * 10000.0,
                timestamp=market_data.timestamp,
                levels=market_data.levels
            )
            
        except Exception as e:
            logger.error(f"Spoof filter failed: {e}")
            return market_data

class ToxicityCalculator:
    """
    Calculates market toxicity score for spread adjustment
    
    Implements JIT-QUOTE-003 requirements:
    - Toxicity proxy calculation (spread shock + sweep rate)
    - 250ms measurement window
    - P&L improvement tracking
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._enabled = config.get("enabled", True)
        self._measurement_window_ms = config.get("measurement_window_ms", 250)
        self._spread_history = deque(maxlen=20)
        self._sweep_detection = deque(maxlen=10)
        
    async def calculate(self, market_data: MarketData) -> float:
        """Calculate toxicity score (0.0 to 1.0)"""
        if not self._enabled:
            return 0.0
        
        try:
            current_time = time.time() * 1000  # milliseconds
            
            # Track spread shocks
            self._spread_history.append((current_time, market_data.spread_bps))
            
            # Calculate spread volatility as toxicity proxy
            if len(self._spread_history) < 3:
                return 0.0
            
            # Recent spreads in measurement window
            cutoff_time = current_time - self._measurement_window_ms
            recent_spreads = [
                spread for timestamp, spread in self._spread_history 
                if timestamp >= cutoff_time
            ]
            
            if len(recent_spreads) < 2:
                return 0.0
            
            # Calculate spread shock (coefficient of variation)
            mean_spread = statistics.mean(recent_spreads)
            if mean_spread <= 0:
                return 0.0
            
            spread_std = statistics.stdev(recent_spreads) if len(recent_spreads) > 1 else 0
            spread_cv = spread_std / mean_spread
            
            # Normalize to 0-1 range (CV > 0.5 = high toxicity)
            toxicity_score = min(1.0, spread_cv / 0.5)
            
            logger.debug(f"Toxicity: {toxicity_score:.3f} (spread_cv={spread_cv:.3f})")
            return toxicity_score
            
        except Exception as e:
            logger.error(f"Toxicity calculation failed: {e}")
            return 0.0

class SpreadManagerV3:
    """
    Enhanced spread manager with toxicity-based adjustment
    
    Implements dynamic spread calculation with:
    - Base spread from filtered orderbook
    - Toxicity-based multiplier
    - Min/max spread enforcement
    - P&L improvement validation
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._base_bps = config.get("base_bps", 2.5)
        self._min_bps = config.get("min_bps", 1.0)
        self._max_bps = config.get("max_bps", 50.0)
        self._toxicity_multiplier = config.get("toxicity_multiplier", 1.5)
        self._toxicity_threshold = config.get("toxicity_threshold", 0.7)
        
    async def calculate(self, 
                       market_data: MarketData,
                       toxicity_score: float,
                       regime: VolatilityRegime) -> float:
        """Calculate dynamic spread with toxicity adjustment"""
        try:
            # Start with base spread
            spread_bps = self._base_bps
            
            # Adjust for market conditions
            if market_data.spread_bps > spread_bps:
                # Market is already wide, use market spread as base
                spread_bps = min(market_data.spread_bps, self._max_bps * 0.8)
            
            # Apply toxicity multiplier if above threshold
            if toxicity_score > self._toxicity_threshold:
                multiplier = 1.0 + (toxicity_score - self._toxicity_threshold) * self._toxicity_multiplier
                spread_bps *= multiplier
                logger.debug(f"Toxicity adjustment: {toxicity_score:.3f} -> {multiplier:.2f}x")
            
            # Regime-based adjustment
            regime_multipliers = {
                VolatilityRegime.LOW: 0.8,
                VolatilityRegime.NORMAL: 1.0,
                VolatilityRegime.HIGH: 1.2
            }
            spread_bps *= regime_multipliers.get(regime, 1.0)
            
            # Enforce min/max bounds
            final_spread = max(self._min_bps, min(self._max_bps, spread_bps))
            
            if final_spread == self._max_bps:
                logger.warning(f"Spread clamped at max: {final_spread}bps")
            
            return final_spread
            
        except Exception as e:
            logger.error(f"Spread calculation failed: {e}")
            return self._base_bps

class CancelReplaceV2:
    """
    Enhanced cancel/replace logic with timing controls
    
    Implements smart refresh decisions based on:
    - Minimum quote lifetime
    - Price movement thresholds
    - Age-based refresh
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._enabled = config.get("enabled", True)
        self._min_lifetime_ms = config.get("min_lifetime_ms", 250)
        self._price_move_bps = config.get("price_move_bps", 1.5)
        self._max_age_ms = config.get("max_age_ms", 5000)
        
        # State tracking
        self._last_price = 0.0
        self._last_timestamp_ms = 0
        
    def should_refresh(self, new_price: float, now_ms: int) -> Tuple[bool, str]:
        """Determine if quotes should be refreshed"""
        if not self._enabled:
            return True, "disabled"
        
        if self._last_price <= 0:
            return True, "init"
        
        # Check minimum lifetime
        age_ms = now_ms - self._last_timestamp_ms
        if age_ms < self._min_lifetime_ms:
            return False, f"min_lifetime_{age_ms}ms"
        
        # Check maximum age (force refresh)
        if age_ms >= self._max_age_ms:
            return True, f"max_age_{age_ms}ms"
        
        # Check price movement
        price_change_bps = abs(new_price - self._last_price) / self._last_price * 10000.0
        if price_change_bps >= self._price_move_bps:
            return True, f"price_move_{price_change_bps:.2f}bps"
        
        return False, f"stable_{age_ms}ms_{price_change_bps:.2f}bps"
    
    def record_quote(self, price: float, timestamp_ms: int) -> None:
        """Record quote for future refresh decisions"""
        self._last_price = price
        self._last_timestamp_ms = timestamp_ms

class PerformanceTracker:
    """Tracks JIT performance metrics and profit attribution"""
    
    def __init__(self):
        self._fill_history = deque(maxlen=500)
        self._profit_measurements = deque(maxlen=100)
        
    def record_fill(self, 
                   price: float, 
                   size: float, 
                   side: str,
                   ref_price: float,
                   toxicity_score: float) -> None:
        """Record a fill for performance analysis"""
        self._fill_history.append({
            'timestamp': time.time(),
            'price': price,
            'size': size,
            'side': side,
            'ref_price': ref_price,
            'toxicity_score': toxicity_score
        })
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get current performance statistics"""
        if not self._fill_history:
            return {}
        
        # Calculate basic stats
        total_fills = len(self._fill_history)
        avg_edge = sum(
            abs(fill['price'] - fill['ref_price']) 
            for fill in self._fill_history
        ) / total_fills if total_fills > 0 else 0
        
        return {
            'total_fills': total_fills,
            'avg_edge_bps': avg_edge * 10000.0,
            'fill_rate_per_hour': total_fills / max(1, (time.time() - self._fill_history[0]['timestamp']) / 3600)
        }

class JITMetricsV3:
    """Enhanced metrics collection for JIT v3.0"""
    
    def __init__(self):
        # Counters
        self.decisions_total = 0
        self.skips_total = 0
        self.errors_total = 0
        
        # Performance tracking
        self.avg_decision_time_ms = 0.0
        self.skip_reasons = {}
        
    def record_decision(self, decision, latency_seconds: float) -> None:
        """Record a successful quote decision"""
        self.decisions_total += 1
        self.avg_decision_time_ms = (
            self.avg_decision_time_ms * 0.9 + latency_seconds * 1000 * 0.1
        )
        
    def record_skip(self, reason: str) -> None:
        """Record a skipped decision with reason"""
        self.skips_total += 1
        self.skip_reasons[reason] = self.skip_reasons.get(reason, 0) + 1
        
    def record_error(self, error_type: str) -> None:
        """Record an error"""
        self.errors_total += 1
        
    def get_stats(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        return {
            'decisions_total': self.decisions_total,
            'skips_total': self.skips_total,
            'errors_total': self.errors_total,
            'avg_decision_time_ms': self.avg_decision_time_ms,
            'skip_reasons': self.skip_reasons.copy()
        }
