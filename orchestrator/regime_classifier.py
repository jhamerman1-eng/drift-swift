#!/usr/bin/env python3
"""
Market Regime Classifier for Drift Trading Bots

Classifies market conditions into different regimes and provides thresholds
for bot decision-making. Integrates with Trend and JIT bot entry logic.
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

import yaml
from loguru import logger

class MarketRegime(Enum):
    """Market regime classifications"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    CONSOLIDATION = "consolidation"

@dataclass
class RegimeThresholds:
    """Thresholds for regime classification"""
    # Trend thresholds
    trend_strength_min: float = 0.5
    trend_duration_min: int = 5

    # Volatility thresholds
    volatility_high_threshold: float = 0.05  # 5% daily volatility
    volatility_low_threshold: float = 0.01   # 1% daily volatility

    # Breakout thresholds
    breakout_volume_multiplier: float = 1.5
    breakout_price_change_pct: float = 0.02  # 2% price change

    # Consolidation thresholds
    consolidation_range_pct: float = 0.01  # 1% range
    consolidation_duration: int = 10

    # Momentum thresholds
    momentum_strong_threshold: float = 0.7
    momentum_weak_threshold: float = 0.3

    # ATR thresholds for choppiness
    atr_choppy_threshold: float = 0.02
    adx_trending_threshold: float = 25.0

    @classmethod
    def from_yaml(cls, config_path: str) -> 'RegimeThresholds':
        """Load thresholds from YAML config"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Extract thresholds section
            thresholds_config = config.get('thresholds', {})

            return cls(
                trend_strength_min=thresholds_config.get('trend_strength_min', 0.5),
                trend_duration_min=thresholds_config.get('trend_duration_min', 5),
                volatility_high_threshold=thresholds_config.get('volatility_high_threshold', 0.05),
                volatility_low_threshold=thresholds_config.get('volatility_low_threshold', 0.01),
                breakout_volume_multiplier=thresholds_config.get('breakout_volume_multiplier', 1.5),
                breakout_price_change_pct=thresholds_config.get('breakout_price_change_pct', 0.02),
                consolidation_range_pct=thresholds_config.get('consolidation_range_pct', 0.01),
                consolidation_duration=thresholds_config.get('consolidation_duration', 10),
                momentum_strong_threshold=thresholds_config.get('momentum_strong_threshold', 0.7),
                momentum_weak_threshold=thresholds_config.get('momentum_weak_threshold', 0.3),
                atr_choppy_threshold=thresholds_config.get('atr_choppy_threshold', 0.02),
                adx_trending_threshold=thresholds_config.get('adx_trending_threshold', 25.0)
            )
        except Exception as e:
            logger.warning(f"Failed to load regime config from {config_path}: {e}")
            logger.info("Using default thresholds")
            return cls()

@dataclass
class MarketData:
    """Market data for regime classification"""
    symbol: str
    price: float
    volume: float
    timestamp: float

    # Technical indicators
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    rsi: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    atr: Optional[float] = None
    adx: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    volume_sma: Optional[float] = None

@dataclass
class RegimeClassification:
    """Regime classification result"""
    regime: MarketRegime
    confidence: float
    indicators: Dict[str, Any]
    timestamp: float
    reasoning: str

class RegimeClassifier:
    """
    Classifies market regimes based on technical indicators and price action.

    Provides regime-aware decision making for trading bots.
    """

    def __init__(self, config_path: str = "configs/regime/thresholds.yaml"):
        self.config_path = config_path
        self.thresholds = RegimeThresholds.from_yaml(config_path)

        # Historical data for trend analysis
        self.price_history: Dict[str, List[MarketData]] = {}
        self.regime_history: Dict[str, List[RegimeClassification]] = {}

        # Cache for recent classifications
        self.regime_cache: Dict[str, RegimeClassification] = {}
        self.cache_timeout = 60  # seconds

        logger.info("🧠 Regime classifier initialized")
        logger.info(f"   Config: {config_path}")
        logger.info(f"   Thresholds loaded: {len(self.thresholds.__dict__)} parameters")

    def classify_regime(self, market_data: MarketData) -> RegimeClassification:
        """
        Classify the current market regime based on technical indicators.

        Args:
            market_data: Current market data with indicators

        Returns:
            RegimeClassification with regime, confidence, and reasoning
        """

        # Check cache first
        cache_key = f"{market_data.symbol}_{int(market_data.timestamp // self.cache_timeout)}"
        if cache_key in self.regime_cache:
            cached = self.regime_cache[cache_key]
            if market_data.timestamp - cached.timestamp < self.cache_timeout:
                return cached

        # Perform classification
        regime, confidence, indicators, reasoning = self._analyze_regime(market_data)

        # Create classification result
        classification = RegimeClassification(
            regime=regime,
            confidence=confidence,
            indicators=indicators,
            timestamp=market_data.timestamp,
            reasoning=reasoning
        )

        # Update cache and history
        self.regime_cache[cache_key] = classification
        self._update_history(market_data.symbol, classification)

        return classification

    def _analyze_regime(self, data: MarketData) -> Tuple[MarketRegime, float, Dict[str, Any], str]:
        """Analyze market data to determine regime"""

        indicators = {}
        reasons = []

        # 1. Check volatility
        volatility_regime = self._classify_volatility(data)
        indicators['volatility'] = volatility_regime.value

        # 2. Check trend strength
        trend_regime, trend_strength = self._classify_trend(data)
        indicators['trend_regime'] = trend_regime.value
        indicators['trend_strength'] = trend_strength

        # 3. Check momentum
        momentum_score = self._calculate_momentum(data)
        indicators['momentum'] = momentum_score

        # 4. Check breakout potential
        breakout_score = self._check_breakout_potential(data)
        indicators['breakout_score'] = breakout_score

        # 5. Check consolidation
        consolidation_score = self._check_consolidation(data)
        indicators['consolidation_score'] = consolidation_score

        # Determine primary regime based on hierarchy
        regime, confidence, reasoning = self._determine_primary_regime(
            volatility_regime, trend_regime, trend_strength,
            momentum_score, breakout_score, consolidation_score
        )

        indicators.update({
            'primary_regime': regime.value,
            'confidence': confidence
        })

        return regime, confidence, indicators, reasoning

    def _classify_volatility(self, data: MarketData) -> MarketRegime:
        """Classify based on volatility levels"""
        if data.atr is None:
            return MarketRegime.SIDEWAYS

        # Calculate recent volatility (simplified - would use actual historical data)
        volatility = data.atr / data.price if data.price > 0 else 0

        if volatility > self.thresholds.volatility_high_threshold:
            return MarketRegime.HIGH_VOLATILITY
        elif volatility < self.thresholds.volatility_low_threshold:
            return MarketRegime.LOW_VOLATILITY
        else:
            return MarketRegime.SIDEWAYS

    def _classify_trend(self, data: MarketData) -> Tuple[MarketRegime, float]:
        """Classify trend direction and strength"""
        if data.adx is None or data.macd_line is None:
            return MarketRegime.SIDEWAYS, 0.0

        # ADX for trend strength
        trend_strength = data.adx / 100.0  # Normalize to 0-1

        # MACD for direction
        macd_diff = data.macd_line - (data.macd_signal or 0)

        # Determine direction
        if trend_strength > self.thresholds.adx_trending_threshold / 100.0:
            if macd_diff > 0:
                return MarketRegime.TRENDING_UP, trend_strength
            else:
                return MarketRegime.TRENDING_DOWN, trend_strength

        return MarketRegime.SIDEWAYS, trend_strength

    def _calculate_momentum(self, data: MarketData) -> float:
        """Calculate momentum score (-1 to 1)"""
        if data.rsi is None:
            return 0.0

        # RSI-based momentum
        rsi_normalized = (data.rsi - 50) / 50  # -1 to 1

        # MACD contribution
        macd_momentum = 0.0
        if data.macd_histogram is not None:
            macd_momentum = min(max(data.macd_histogram / abs(data.price * 0.001), -1), 1)

        # Combine RSI and MACD
        momentum = (rsi_normalized * 0.6) + (macd_momentum * 0.4)

        return min(max(momentum, -1), 1)

    def _check_breakout_potential(self, data: MarketData) -> float:
        """Check for breakout potential (0-1 scale)"""
        if not all([data.bollinger_upper, data.bollinger_lower, data.volume_sma]):
            return 0.0

        # Price near Bollinger Bands
        upper_dist = abs(data.price - data.bollinger_upper) / data.price if data.bollinger_upper is not None else 1.0
        lower_dist = abs(data.price - data.bollinger_lower) / data.price if data.bollinger_lower is not None else 1.0
        band_proximity = 1 - min(upper_dist, lower_dist) / 0.05  # Closer to bands = higher score

        # Volume spike
        if data.volume_sma is not None and data.volume_sma > 0:
            volume_ratio = data.volume / data.volume_sma
        else:
            volume_ratio = 1
        volume_score = min(volume_ratio / 2, 1)  # Cap at 2x volume

        return min(band_proximity * volume_score, 1)

    def _check_consolidation(self, data: MarketData) -> float:
        """Check for consolidation (0-1 scale, higher = more consolidated)"""
        if not all([data.bollinger_upper, data.bollinger_lower]):
            return 0.0

        # Bollinger Band width (narrower = more consolidated)
        if data.bollinger_upper is None or data.bollinger_lower is None or data.price is None or data.price == 0:
            return 0.0
        bb_width = (data.bollinger_upper - data.bollinger_lower) / data.price
        consolidation_score = max(0, 1 - (bb_width / 0.1))  # Normalize to 0-1

        return consolidation_score

    def _determine_primary_regime(self, volatility_regime: MarketRegime,
                                trend_regime: MarketRegime, trend_strength: float,
                                momentum: float, breakout_score: float,
                                consolidation_score: float) -> Tuple[MarketRegime, float, str]:
        """Determine the primary market regime based on all indicators"""

        # High priority: Breakout
        if breakout_score > 0.7:
            return MarketRegime.BREAKOUT, breakout_score, "Strong breakout signals detected"

        # High priority: High volatility
        if volatility_regime == MarketRegime.HIGH_VOLATILITY:
            return MarketRegime.HIGH_VOLATILITY, 0.8, "High volatility environment"

        # Trending regimes
        if trend_regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            if trend_strength > 0.7:
                return trend_regime, trend_strength, f"Strong {trend_regime.value.replace('_', ' ')}"

        # Consolidation
        if consolidation_score > 0.8:
            return MarketRegime.CONSOLIDATION, consolidation_score, "Market in consolidation phase"

        # Low volatility
        if volatility_regime == MarketRegime.LOW_VOLATILITY:
            return MarketRegime.LOW_VOLATILITY, 0.6, "Low volatility, ranging market"

        # Default to sideways
        return MarketRegime.SIDEWAYS, 0.5, "Sideways/market in equilibrium"

    def _update_history(self, symbol: str, classification: RegimeClassification):
        """Update regime history for the symbol"""
        if symbol not in self.regime_history:
            self.regime_history[symbol] = []

        self.regime_history[symbol].append(classification)

        # Keep only last 100 classifications
        if len(self.regime_history[symbol]) > 100:
            self.regime_history[symbol] = self.regime_history[symbol][-100:]

    def get_regime_history(self, symbol: str, limit: int = 10) -> List[RegimeClassification]:
        """Get recent regime classifications for a symbol"""
        return self.regime_history.get(symbol, [])[-limit:]

    def get_regime_stats(self, symbol: str) -> Dict[str, Any]:
        """Get regime statistics for a symbol"""
        history = self.regime_history.get(symbol, [])

        if not history:
            return {"error": "No regime history available"}

        # Calculate regime distribution
        regime_counts = {}
        for classification in history:
            regime = classification.regime.value
            regime_counts[regime] = regime_counts.get(regime, 0) + 1

        total = len(history)
        regime_distribution = {
            regime: count / total
            for regime, count in regime_counts.items()
        }

        # Current regime
        current = history[-1] if history else None

        return {
            "current_regime": current.regime.value if current else None,
            "current_confidence": current.confidence if current else None,
            "regime_distribution": regime_distribution,
            "total_classifications": total,
            "symbol": symbol
        }

    def is_regime_favorable_for_trend_bot(self, classification: RegimeClassification) -> bool:
        """Check if current regime is favorable for trend-following strategies"""
        favorable_regimes = [
            MarketRegime.TRENDING_UP,
            MarketRegime.TRENDING_DOWN,
            MarketRegime.BREAKOUT
        ]

        return (classification.regime in favorable_regimes and
                classification.confidence > 0.6)

    def is_regime_favorable_for_jit_bot(self, classification: RegimeClassification) -> bool:
        """Check if current regime is favorable for JIT market-making"""
        # JIT prefers moderate volatility and consolidation
        favorable_regimes = [
            MarketRegime.LOW_VOLATILITY,
            MarketRegime.SIDEWAYS,
            MarketRegime.CONSOLIDATION
        ]

        # Avoid high volatility and strong trends
        unfavorable_regimes = [
            MarketRegime.HIGH_VOLATILITY,
            MarketRegime.TRENDING_UP,
            MarketRegime.TRENDING_DOWN
        ]

        if classification.regime in unfavorable_regimes:
            return False

        return (classification.regime in favorable_regimes or
                classification.confidence < 0.7)  # Moderate confidence regimes

    def get_regime_adjusted_parameters(self, base_params: Dict[str, Any],
                                     regime: MarketRegime) -> Dict[str, Any]:
        """Adjust trading parameters based on market regime"""
        adjusted = base_params.copy()

        # Regime-specific adjustments
        if regime == MarketRegime.HIGH_VOLATILITY:
            # Increase spreads, reduce position sizes
            adjusted['spread_multiplier'] = adjusted.get('spread_multiplier', 1.0) * 1.5
            adjusted['max_position_size'] = adjusted.get('max_position_size', 1.0) * 0.7

        elif regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            # Increase trend-following aggressiveness
            adjusted['momentum_weight'] = adjusted.get('momentum_weight', 1.0) * 1.3

        elif regime == MarketRegime.LOW_VOLATILITY:
            # Tighten spreads, increase frequency
            adjusted['spread_multiplier'] = adjusted.get('spread_multiplier', 1.0) * 0.8
            adjusted['quote_frequency'] = adjusted.get('quote_frequency', 1.0) * 1.2

        elif regime == MarketRegime.CONSOLIDATION:
            # Optimize for ranging markets
            adjusted['range_weight'] = adjusted.get('range_weight', 1.0) * 1.2

        return adjusted

# Global classifier instance
_classifier_instance: Optional[RegimeClassifier] = None

def get_regime_classifier() -> RegimeClassifier:
    """Get the global regime classifier instance"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = RegimeClassifier()
    return _classifier_instance

if __name__ == "__main__":
    # Test the classifier
    classifier = RegimeClassifier()

    # Sample market data
    sample_data = MarketData(
        symbol="SOL-PERP",
        price=150.0,
        volume=1000000,
        timestamp=time.time(),
        sma_20=148.0,
        sma_50=145.0,
        rsi=65.0,
        macd_line=1.2,
        macd_signal=0.8,
        macd_histogram=0.4,
        atr=2.5,
        adx=30.0,
        bollinger_upper=155.0,
        bollinger_lower=145.0,
        volume_sma=800000
    )

    # Classify
    result = classifier.classify_regime(sample_data)

    print("🧠 Market Regime Classification Test")
    print(f"Symbol: {sample_data.symbol}")
    print(f"Regime: {result.regime.value}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Reasoning: {result.reasoning}")
    print(f"Indicators: {json.dumps(result.indicators, indent=2)}")
