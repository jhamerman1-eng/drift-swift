#!/usr/bin/env python3
"""
JIT Bot Regime Integration

Integrates market regime classification into JIT market making decisions.
Adjusts spreads, position limits, and quoting behavior based on market conditions.
"""

from orchestrator.regime_classifier import get_regime_classifier, MarketRegime, MarketData
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class JITRegimeIntegration:
    """
    Integrates regime classification into JIT market making logic.

    Provides regime-aware adjustments for:
    - Spread calculations
    - Position limits
    - Order sizing
    - Inventory management
    """

    def __init__(self):
        self.classifier = get_regime_classifier()
        self.last_regime: Optional[MarketRegime] = None
        self.regime_stability_counter = 0

        logger.info("JIT Regime Integration initialized")

    def should_quote_in_regime(self, symbol: str, price: float, volume: float,
                              rsi: Optional[float] = None,
                              atr: Optional[float] = None,
                              adx: Optional[float] = None) -> Tuple[bool, str]:
        """
        Determine if JIT should continue quoting based on market regime.

        Returns:
            Tuple of (should_quote: bool, reason: str)
        """

        try:
            # Create market data
            import time
            market_data = MarketData(
                symbol=symbol,
                price=price,
                volume=volume,
                timestamp=time.time(),
                rsi=rsi,
                atr=atr,
                adx=adx
            )

            # Classify regime
            classification = self.classifier.classify_regime(market_data)

            # Update regime stability tracking
            if classification.regime == self.last_regime:
                self.regime_stability_counter += 1
            else:
                self.regime_stability_counter = 1
                self.last_regime = classification.regime

            # Check if regime is favorable for JIT
            is_favorable = self.classifier.is_regime_favorable_for_jit_bot(classification)

            if is_favorable:
                reason = f"Regime {classification.regime.value} favorable for JIT (confidence: {classification.confidence:.2f})"
                return True, reason
            else:
                reason = f"Regime {classification.regime.value} not favorable for JIT (confidence: {classification.confidence:.2f})"
                return False, reason

        except Exception as e:
            logger.warning(f"Regime check failed, defaulting to allow quoting: {e}")
            return True, f"Regime check failed: {e}"

    def get_regime_adjusted_spreads(self, base_spread_bps: float,
                                   regime: Optional[MarketRegime] = None,
                                   symbol: str = "", price: float = 0.0,
                                   volume: float = 0.0) -> float:
        """
        Adjust spread based on market regime.

        Args:
            base_spread_bps: Base spread in basis points
            regime: Optional pre-classified regime
            symbol, price, volume: Market data for classification if regime not provided

        Returns:
            Adjusted spread in basis points
        """

        # Get regime if not provided
        if regime is None:
            try:
                import time
                market_data = MarketData(symbol=symbol, price=price, volume=volume, timestamp=time.time())
                classification = self.classifier.classify_regime(market_data)
                regime = classification.regime
            except Exception as e:
                logger.warning(f"Failed to classify regime for spread adjustment: {e}")
                return base_spread_bps

        # Apply regime-specific adjustments
        if regime == MarketRegime.HIGH_VOLATILITY:
            # Increase spreads in high volatility
            adjusted_spread = base_spread_bps * 1.5
            logger.debug(f"High volatility: increasing spread to {adjusted_spread:.1f}bps")

        elif regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            # Slightly increase spreads during strong trends
            adjusted_spread = base_spread_bps * 1.2
            logger.debug(f"Strong trend: increasing spread to {adjusted_spread:.1f}bps")

        elif regime == MarketRegime.LOW_VOLATILITY:
            # Tighten spreads in low volatility
            adjusted_spread = base_spread_bps * 0.8
            logger.debug(f"Low volatility: tightening spread to {adjusted_spread:.1f}bps")

        elif regime == MarketRegime.CONSOLIDATION:
            # Moderate spreads in consolidation
            adjusted_spread = base_spread_bps * 0.9
            logger.debug(f"Consolidation: moderate spread to {adjusted_spread:.1f}bps")

        else:
            # Default spreads for sideways/choppy markets
            adjusted_spread = base_spread_bps
            logger.debug(f"Sideways market: using base spread {adjusted_spread:.1f}bps")

        # Ensure spreads stay within reasonable bounds
        min_spread = base_spread_bps * 0.5
        max_spread = base_spread_bps * 3.0
        adjusted_spread = max(min_spread, min(max_spread, adjusted_spread))

        return adjusted_spread

    def get_regime_adjusted_position_limits(self, base_max_position: float,
                                          regime: Optional[MarketRegime] = None,
                                          symbol: str = "", price: float = 0.0,
                                          volume: float = 0.0) -> float:
        """
        Adjust position limits based on market regime.

        Args:
            base_max_position: Base maximum position size
            regime: Optional pre-classified regime
            symbol, price, volume: Market data for classification if regime not provided

        Returns:
            Adjusted maximum position size
        """

        # Get regime if not provided
        if regime is None:
            try:
                import time
                market_data = MarketData(symbol=symbol, price=price, volume=volume, timestamp=time.time())
                classification = self.classifier.classify_regime(market_data)
                regime = classification.regime
            except Exception as e:
                logger.warning(f"Failed to classify regime for position limit adjustment: {e}")
                return base_max_position

        # Apply regime-specific adjustments
        if regime == MarketRegime.HIGH_VOLATILITY:
            # Reduce position limits in high volatility
            adjusted_limit = base_max_position * 0.6
            logger.debug(f"High volatility: reducing position limit to {adjusted_limit:.2f}")

        elif regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            # Maintain normal limits during trends (trends can be good for inventory)
            adjusted_limit = base_max_position
            logger.debug(f"Strong trend: maintaining position limit at {adjusted_limit:.2f}")

        elif regime == MarketRegime.LOW_VOLATILITY:
            # Can be more aggressive in low volatility
            adjusted_limit = base_max_position * 1.2
            logger.debug(f"Low volatility: increasing position limit to {adjusted_limit:.2f}")

        elif regime == MarketRegime.CONSOLIDATION:
            # Conservative in consolidation
            adjusted_limit = base_max_position * 0.8
            logger.debug(f"Consolidation: reducing position limit to {adjusted_limit:.2f}")

        else:
            # Default for sideways markets
            adjusted_limit = base_max_position
            logger.debug(f"Sideways market: using base position limit {adjusted_limit:.2f}")

        # Ensure limits stay reasonable
        min_limit = base_max_position * 0.3
        max_limit = base_max_position * 2.0
        adjusted_limit = max(min_limit, min(max_limit, adjusted_limit))

        return adjusted_limit

    def get_regime_adjusted_order_sizes(self, base_bid_size: float, base_ask_size: float,
                                       inventory_skew: float,
                                       regime: Optional[MarketRegime] = None,
                                       symbol: str = "", price: float = 0.0,
                                       volume: float = 0.0) -> Tuple[float, float]:
        """
        Adjust order sizes based on market regime and inventory skew.

        Args:
            base_bid_size: Base bid order size
            base_ask_size: Base ask order size
            inventory_skew: Current inventory skew (-1 to 1)
            regime: Optional pre-classified regime
            symbol, price, volume: Market data for classification if regime not provided

        Returns:
            Tuple of (adjusted_bid_size, adjusted_ask_size)
        """

        # Get regime if not provided
        if regime is None:
            try:
                import time
                market_data = MarketData(symbol=symbol, price=price, volume=volume, timestamp=time.time())
                classification = self.classifier.classify_regime(market_data)
                regime = classification.regime
            except Exception as e:
                logger.warning(f"Failed to classify regime for order size adjustment: {e}")
                return base_bid_size, base_ask_size

        # Base adjustment for inventory skew (existing logic)
        inventory_multiplier = 1.0 - abs(inventory_skew) * 0.5
        bid_size = base_bid_size * inventory_multiplier
        ask_size = base_ask_size * inventory_multiplier

        # Additional regime-specific adjustments
        if regime == MarketRegime.HIGH_VOLATILITY:
            # Reduce sizes in high volatility
            regime_multiplier = 0.7
        elif regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            # Reduce sizes during strong trends to avoid adverse selection
            regime_multiplier = 0.8
        elif regime == MarketRegime.LOW_VOLATILITY:
            # Can be slightly more aggressive in low volatility
            regime_multiplier = 1.1
        elif regime == MarketRegime.CONSOLIDATION:
            # Conservative in consolidation
            regime_multiplier = 0.9
        else:
            # Default for sideways markets
            regime_multiplier = 1.0

        bid_size *= regime_multiplier
        ask_size *= regime_multiplier

        # Ensure minimum sizes
        min_size = 0.01  # Minimum order size
        bid_size = max(min_size, bid_size)
        ask_size = max(min_size, ask_size)

        logger.debug(f"Regime {regime.value}: adjusted sizes - Bid: {bid_size:.3f}, Ask: {ask_size:.3f}")

        return bid_size, ask_size

    def get_regime_trading_frequency(self, base_frequency: float,
                                    regime: Optional[MarketRegime] = None,
                                    symbol: str = "", price: float = 0.0,
                                    volume: float = 0.0) -> float:
        """
        Adjust trading frequency based on market regime.

        Args:
            base_frequency: Base quotes per second
            regime: Optional pre-classified regime
            symbol, price, volume: Market data for classification if regime not provided

        Returns:
            Adjusted quotes per second
        """

        # Get regime if not provided
        if regime is None:
            try:
                import time
                market_data = MarketData(symbol=symbol, price=price, volume=volume, timestamp=time.time())
                classification = self.classifier.classify_regime(market_data)
                regime = classification.regime
            except Exception as e:
                logger.warning(f"Failed to classify regime for frequency adjustment: {e}")
                return base_frequency

        # Apply regime-specific frequency adjustments
        if regime == MarketRegime.HIGH_VOLATILITY:
            # Reduce frequency in high volatility
            adjusted_freq = base_frequency * 0.5
        elif regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            # Reduce frequency during strong trends
            adjusted_freq = base_frequency * 0.7
        elif regime == MarketRegime.LOW_VOLATILITY:
            # Increase frequency in low volatility
            adjusted_freq = base_frequency * 1.3
        elif regime == MarketRegime.CONSOLIDATION:
            # Moderate frequency in consolidation
            adjusted_freq = base_frequency * 0.9
        else:
            # Default frequency for sideways markets
            adjusted_freq = base_frequency

        # Ensure reasonable bounds
        min_freq = base_frequency * 0.1
        max_freq = base_frequency * 3.0
        adjusted_freq = max(min_freq, min(max_freq, adjusted_freq))

        return adjusted_freq

    def get_regime_status(self) -> Dict[str, Any]:
        """Get current regime integration status."""
        return {
            "current_regime": self.last_regime.value if self.last_regime else None,
            "regime_stability_counter": self.regime_stability_counter,
            "classifier_available": True
        }


# Global instance
_jit_regime_integration: Optional[JITRegimeIntegration] = None

def get_jit_regime_integration() -> JITRegimeIntegration:
    """Get the global JIT regime integration instance."""
    global _jit_regime_integration
    if _jit_regime_integration is None:
        _jit_regime_integration = JITRegimeIntegration()
    return _jit_regime_integration


