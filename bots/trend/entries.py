"""Regime-based entries using the market regime classifier."""

from orchestrator.regime_classifier import get_regime_classifier, MarketRegime, MarketData
from typing import Optional


def entry_allowed(regime: str) -> bool:
    """
    Legacy function for backward compatibility.
    Use regime_classifier_entry_allowed() instead.
    """
    return regime in ("trend", "breakout")


def regime_classifier_entry_allowed(symbol: str, price: float, volume: float,
                                   rsi: Optional[float] = None,
                                   macd_line: Optional[float] = None,
                                   macd_signal: Optional[float] = None,
                                   atr: Optional[float] = None,
                                   adx: Optional[float] = None,
                                   bollinger_upper: Optional[float] = None,
                                   bollinger_lower: Optional[float] = None) -> bool:
    """
    Check if trend entry is allowed based on market regime classification.

    Uses the regime classifier to determine if current market conditions
    are favorable for trend-following strategies.

    Args:
        symbol: Trading symbol (e.g., "SOL-PERP")
        price: Current market price
        volume: Current trading volume
        rsi: RSI indicator value (0-100)
        macd_line: MACD line value
        macd_signal: MACD signal line value
        atr: Average True Range
        adx: Average Directional Index
        bollinger_upper: Upper Bollinger Band
        bollinger_lower: Lower Bollinger Band

    Returns:
        True if trend entry is allowed, False otherwise
    """

    try:
        # Get the regime classifier
        classifier = get_regime_classifier()

        # Create market data object
        import time
        market_data = MarketData(
            symbol=symbol,
            price=price,
            volume=volume,
            timestamp=time.time(),
            rsi=rsi,
            macd_line=macd_line,
            macd_signal=macd_signal,
            atr=atr,
            adx=adx,
            bollinger_upper=bollinger_upper,
            bollinger_lower=bollinger_lower
        )

        # Classify regime
        classification = classifier.classify_regime(market_data)

        # Check if regime is favorable for trend following
        return classifier.is_regime_favorable_for_trend_bot(classification)

    except Exception as e:
        # On error, default to allowing entries (fail-safe)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Regime classification failed, defaulting to allow entry: {e}")
        return True


def get_regime_adjusted_trend_params(base_params: dict, symbol: str, price: float, volume: float,
                                    **indicators) -> dict:
    """
    Adjust trend bot parameters based on current market regime.

    Args:
        base_params: Base trend bot configuration parameters
        symbol: Trading symbol
        price: Current price
        volume: Current volume
        **indicators: Technical indicators (rsi, macd_line, etc.)

    Returns:
        Adjusted parameters dictionary
    """

    try:
        classifier = get_regime_classifier()

        # Create market data
        import time
        market_data = MarketData(
            symbol=symbol,
            price=price,
            volume=volume,
            timestamp=time.time(),
            **indicators
        )

        # Classify regime
        classification = classifier.classify_regime(market_data)

        # Get regime-adjusted parameters
        adjusted = classifier.get_regime_adjusted_parameters(
            base_params, classification.regime
        )

        return adjusted

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Regime parameter adjustment failed, using base params: {e}")
        return base_params.copy()
