"""
Advanced Quote Engine - Funding-Skewed Quotes & Impact-Aware Bands

Sophisticated market making engine that implements:
1. Funding-skewed quote adapter (widen narrow side when funding unfavorable, tighten when favorable)
2. Impact-aware inventory bands (use AMM price elasticity + L2 depth to shape band edges)
3. Unified fair-value calculation (oracle ± AMM microprice blend) for OBI/microprice signal

Key Features:
- Dynamic quote adjustment based on funding rates
- Inventory management with market impact awareness
- Fair value calculation blending oracle and AMM signals
- Real-time adaptation to market conditions
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from decimal import Decimal
from dataclasses import dataclass, field
from datetime import datetime
from libs.util.decimal import D

from ..drift.drift_market_adapter import (
    PerpMarket, PERCENTAGE_PRECISION
)
from ..orderbook.l2_orderbook_engine import (
    L2OrderBookEngine, L2OrderBook
)

logger = logging.getLogger(__name__)

@dataclass
class QuoteAdjustment:
    """Quote adjustment parameters"""
    bid_spread_adjustment: Decimal = Decimal('0')  # Additional spread for bids
    ask_spread_adjustment: Decimal = Decimal('0')  # Additional spread for asks
    band_edge_adjustment: Decimal = Decimal('0')   # Band edge movement
    reason: str = ""
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

@dataclass
class InventoryBand:
    """Inventory band parameters"""
    bid_edge: Decimal
    ask_edge: Decimal
    band_width: Decimal
    inventory_target: Decimal = Decimal('0')
    adjustment_factor: Decimal = Decimal('1')
    last_update: float = field(default_factory=lambda: datetime.now().timestamp())

@dataclass
class FairValueSignal:
    """Unified fair value signal"""
    fair_price: Decimal
    oracle_weight: Decimal
    amm_weight: Decimal
    confidence_score: Decimal
    signal_components: Dict[str, Decimal] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

class FundingSkewedQuoteAdapter:
    """
    Funding-Skewed Quote Adapter

    Adjusts quotes based on funding rates:
    - Widen narrow side when funding unfavorable
    - Tighten when favorable
    - Incentivize position balancing
    """

    def __init__(
        self,
        max_funding_skew: Decimal = Decimal('0.0005'),  # 0.05% max normal funding
        funding_sensitivity: Decimal = Decimal('1000'), # Sensitivity multiplier
        adaptation_speed: Decimal = Decimal('0.1'),     # How quickly to adapt (0-1)
        min_spread_adjustment: Decimal = Decimal('0.0001'),  # 0.01% minimum
        max_spread_adjustment: Decimal = Decimal('0.01')     # 1% maximum
    ):
        self.max_funding_skew = max_funding_skew
        self.funding_sensitivity = funding_sensitivity
        self.adaptation_speed = adaptation_speed
        self.min_spread_adjustment = min_spread_adjustment
        self.max_spread_adjustment = max_spread_adjustment

        # State tracking
        self.last_funding_rate = Decimal('0')
        self.adjustment_history: List[QuoteAdjustment] = []
        self.funding_regime = "neutral"

    def calculate_funding_skew_adjustment(
        self,
        funding_rate: Decimal,
        position_imbalance: Decimal,
        market_regime: str = "normal"
    ) -> QuoteAdjustment:
        """
        Calculate quote adjustment based on funding rate skew

        Args:
            funding_rate: Current funding rate (can be positive or negative)
            position_imbalance: Current position imbalance (-1 to 1, negative = short bias)
            market_regime: Current market regime ("volatile", "calm", "toxic")

        Returns:
            QuoteAdjustment with bid/ask spread adjustments
        """
        # Determine funding regime
        if abs(funding_rate) < self.max_funding_skew:
            self.funding_regime = "neutral"
            adjustment = Decimal('0')
        elif funding_rate > 0:
            self.funding_regime = "long_pay_short"
            # Longs are paying shorts - incentivize short positions
            # Widen bid side (make it less attractive to buy)
            adjustment = min(
                funding_rate * self.funding_sensitivity,
                self.max_spread_adjustment
            )
        else:
            self.funding_regime = "short_pay_long"
            # Shorts are paying longs - incentivize long positions
            # Widen ask side (make it less attractive to sell)
            adjustment = min(
                abs(funding_rate) * self.funding_sensitivity,
                self.max_spread_adjustment
            )

        # Apply adaptation speed (gradual changes)
        if self.last_funding_rate != 0:
            adjustment = self.last_funding_rate * (Decimal('1') - self.adaptation_speed) + \
                        adjustment * self.adaptation_speed

        self.last_funding_rate = adjustment

        # Apply market regime adjustments
        regime_multiplier = self._get_regime_multiplier(market_regime)
        adjustment = adjustment * regime_multiplier

        # Ensure minimum adjustment
        if abs(adjustment) < self.min_spread_adjustment and adjustment != 0:
            adjustment = self.min_spread_adjustment * (Decimal('1') if adjustment > 0 else Decimal('-1'))

        # Position imbalance consideration
        imbalance_adjustment = self._calculate_imbalance_adjustment(position_imbalance)
        total_adjustment = adjustment + imbalance_adjustment

        # Create adjustment result
        if funding_rate > 0:
            # Longs paying shorts - widen bid side
            result = QuoteAdjustment(
                bid_spread_adjustment=total_adjustment,
                ask_spread_adjustment=Decimal('0'),
                reason=f"Funding skew: longs pay shorts ({funding_rate:.6%}), widening bids"
            )
        elif funding_rate < 0:
            # Shorts paying longs - widen ask side
            result = QuoteAdjustment(
                bid_spread_adjustment=Decimal('0'),
                ask_spread_adjustment=total_adjustment,
                reason=f"Funding skew: shorts pay longs ({funding_rate:.6%}), widening asks"
            )
        else:
            result = QuoteAdjustment(
                reason="Neutral funding regime"
            )

        self.adjustment_history.append(result)
        if len(self.adjustment_history) > 100:  # Keep last 100 adjustments
            self.adjustment_history.pop(0)

        return result

    def _get_regime_multiplier(self, market_regime: str) -> Decimal:
        """Get adjustment multiplier based on market regime"""
        multipliers = {
            "calm": Decimal('0.5'),      # Less aggressive in calm markets
            "normal": Decimal('1.0'),    # Normal adjustment
            "volatile": Decimal('1.5'),  # More aggressive in volatile markets
            "toxic": Decimal('2.0')      # Very aggressive in toxic markets
        }
        return multipliers.get(market_regime, Decimal('1.0'))

    def _calculate_imbalance_adjustment(self, position_imbalance: Decimal) -> Decimal:
        """Calculate additional adjustment based on position imbalance"""
        if abs(position_imbalance) < Decimal('0.1'):
            return Decimal('0')

        # Additional adjustment for severe imbalance
        imbalance_factor = abs(position_imbalance) - Decimal('0.1')
        adjustment = imbalance_factor * Decimal('0.001')  # 0.1% per 10% imbalance

        return adjustment if position_imbalance > 0 else -adjustment

    def get_adjustment_statistics(self) -> Dict[str, Any]:
        """Get statistics about funding adjustments"""
        if not self.adjustment_history:
            return {"error": "No adjustment history"}

        recent_adjustments = self.adjustment_history[-50:]  # Last 50 adjustments

        bid_adjustments = [adj.bid_spread_adjustment for adj in recent_adjustments if adj.bid_spread_adjustment != 0]
        ask_adjustments = [adj.ask_spread_adjustment for adj in recent_adjustments if adj.ask_spread_adjustment != 0]

        stats = {
            "total_adjustments": len(recent_adjustments),
            "funding_regime": self.funding_regime,
            "last_funding_rate": float(self.last_funding_rate),
            "avg_bid_adjustment": float(sum(bid_adjustments) / len(bid_adjustments)) if bid_adjustments else 0,
            "avg_ask_adjustment": float(sum(ask_adjustments) / len(ask_adjustments)) if ask_adjustments else 0,
            "max_bid_adjustment": float(max(bid_adjustments)) if bid_adjustments else 0,
            "max_ask_adjustment": float(max(ask_adjustments)) if ask_adjustments else 0,
            "bid_adjustment_frequency": len(bid_adjustments) / len(recent_adjustments),
            "ask_adjustment_frequency": len(ask_adjustments) / len(recent_adjustments)
        }

        return stats

class ImpactAwareInventoryBands:
    """
    Impact-Aware Inventory Bands

    Uses AMM price elasticity + L2 depth to shape band edges:
    - Dynamic band width based on market conditions
    - L2 depth awareness for impact estimation
    - AMM elasticity modeling
    - Real-time band adjustment
    """

    def __init__(
        self,
        base_band_width: Decimal = Decimal('0.005'),      # 0.5% base band
        max_band_width: Decimal = Decimal('0.05'),        # 5% maximum band
        l2_depth_sensitivity: Decimal = Decimal('0.8'),   # L2 depth impact
        amm_elasticity_factor: Decimal = Decimal('0.1'),  # AMM elasticity
        adaptation_rate: Decimal = Decimal('0.1'),        # How quickly to adapt
        inventory_target: Decimal = Decimal('0'),         # Target inventory level
        max_inventory_deviation: Decimal = Decimal('0.2')  # Max allowed deviation
    ):
        self.base_band_width = base_band_width
        self.max_band_width = max_band_width
        self.l2_depth_sensitivity = l2_depth_sensitivity
        self.amm_elasticity_factor = amm_elasticity_factor
        self.adaptation_rate = adaptation_rate
        self.inventory_target = inventory_target
        self.max_inventory_deviation = max_inventory_deviation

        # State tracking
        self.current_band = InventoryBand(
            bid_edge=Decimal('0'),
            ask_edge=Decimal('0'),
            band_width=base_band_width
        )
        self.band_history: List[InventoryBand] = []
        self.last_base_price = Decimal('0')

    async def calculate_impact_aware_bands(
        self,
        base_price: Decimal,
        current_inventory: Decimal,
        l2_orderbook: Optional[L2OrderBook] = None,
        market_regime: str = "normal",
        amm_elasticity: Optional[Decimal] = None
    ) -> InventoryBand:
        """
        Calculate impact-aware inventory bands

        Args:
            base_price: Base price for band calculation
            current_inventory: Current inventory level (normalized -1 to 1)
            l2_orderbook: L2 order book for depth analysis
            market_regime: Current market regime
            amm_elasticity: AMM price elasticity factor

        Returns:
            InventoryBand with calculated edges and width
        """
        # Use provided elasticity or default
        elasticity = amm_elasticity or self.amm_elasticity_factor

        # Base band width
        band_width = self.base_band_width

        # Inventory deviation adjustment
        inventory_deviation = abs(current_inventory - self.inventory_target)
        if inventory_deviation > self.max_inventory_deviation:
            # Severe deviation - significantly widen bands
            deviation_factor = (inventory_deviation - self.max_inventory_deviation) * Decimal('10')
            band_width += deviation_factor
        else:
            # Normal deviation - moderate adjustment
            deviation_factor = inventory_deviation * Decimal('2')
            band_width += deviation_factor

        # L2 depth analysis
        l2_depth_factor = Decimal('0')
        if l2_orderbook:
            l2_depth_info = self._analyze_l2_depth(l2_orderbook, base_price)
            l2_depth_factor = l2_depth_info['depth_factor']

            # Apply L2 depth sensitivity
            band_width += l2_depth_factor * self.l2_depth_sensitivity

        # AMM elasticity adjustment
        elasticity_adjustment = elasticity * Decimal('0.01')  # Convert to percentage
        band_width += elasticity_adjustment

        # Market regime adjustment
        regime_multiplier = self._get_regime_band_multiplier(market_regime)
        band_width *= regime_multiplier

        # Clamp to maximum
        band_width = min(band_width, self.max_band_width)

        # Apply adaptation rate (gradual changes)
        if self.current_band.band_width > 0:
            band_width = self.current_band.band_width * (Decimal('1') - self.adaptation_rate) + \
                        band_width * self.adaptation_rate

        # Calculate band edges
        bid_edge = base_price * (Decimal('1') - band_width)
        ask_edge = base_price * (Decimal('1') + band_width)

        # Update current band
        self.current_band = InventoryBand(
            bid_edge=bid_edge,
            ask_edge=ask_edge,
            band_width=band_width,
            inventory_target=self.inventory_target,
            adjustment_factor=Decimal('1'),
            last_update=datetime.now().timestamp()
        )

        self.last_base_price = base_price
        self.band_history.append(self.current_band)
        if len(self.band_history) > 100:  # Keep last 100 bands
            self.band_history.pop(0)

        return self.current_band

    def _analyze_l2_depth(self, l2_orderbook: L2OrderBook, base_price: Decimal) -> Dict[str, Decimal]:
        """Analyze L2 depth for band width adjustment"""
        # Get depth at different price levels
        depth_levels = [Decimal('0.001'), Decimal('0.005'), Decimal('0.01')]  # 0.1%, 0.5%, 1%

        total_depth = Decimal('0')
        depth_points = 0

        for depth_pct in depth_levels:
            # Calculate price levels
            bid_price_level = base_price * (Decimal('1') - depth_pct)
            ask_price_level = base_price * (Decimal('1') + depth_pct)

            # Get depth at these levels
            bid_depth = l2_orderbook.get_depth_at_price(bid_price_level, 'bid')
            ask_depth = l2_orderbook.get_depth_at_price(ask_price_level, 'ask')

            level_depth = min(bid_depth, ask_depth)
            total_depth += level_depth
            depth_points += 1

        avg_depth = total_depth / Decimal(str(depth_points)) if depth_points > 0 else Decimal('0')

        # Calculate depth factor (inverse relationship - less depth = wider bands)
        if avg_depth > 0:
            depth_factor = Decimal('1000000') / avg_depth  # Scale factor
            depth_factor = min(depth_factor * Decimal('0.0001'), Decimal('0.01'))  # Cap at 1%
        else:
            depth_factor = Decimal('0.01')  # Maximum adjustment for no depth

        return {
            'avg_depth': avg_depth,
            'depth_factor': depth_factor,
            'bid_depth': l2_orderbook.get_depth_at_price(base_price * Decimal('0.995'), 'bid'),
            'ask_depth': l2_orderbook.get_depth_at_price(base_price * Decimal('1.005'), 'ask')
        }

    def _get_regime_band_multiplier(self, market_regime: str) -> Decimal:
        """Get band width multiplier based on market regime"""
        multipliers = {
            "calm": Decimal('0.7'),      # Narrower bands in calm markets
            "normal": Decimal('1.0'),    # Normal band width
            "volatile": Decimal('1.5'),  # Wider bands in volatile markets
            "toxic": Decimal('2.0')      # Much wider bands in toxic markets
        }
        return multipliers.get(market_regime, Decimal('1.0'))

    def get_band_statistics(self) -> Dict[str, Any]:
        """Get statistics about band adjustments"""
        if not self.band_history:
            return {"error": "No band history"}

        recent_bands = self.band_history[-50:]  # Last 50 bands

        band_widths = [band.band_width for band in recent_bands]

        stats = {
            "total_bands": len(recent_bands),
            "current_band_width": float(self.current_band.band_width),
            "avg_band_width": float(sum(band_widths) / len(band_widths)),
            "min_band_width": float(min(band_widths)),
            "max_band_width": float(max(band_widths)),
            "band_width_volatility": float(self._calculate_volatility(band_widths)),
            "last_update": self.current_band.last_update
        }

        return stats

    def _calculate_volatility(self, values: List[Decimal]) -> Decimal:
        """Calculate volatility of band widths"""
        if len(values) < 2:
            return Decimal('0')

        # Convert all values to Decimal for consistent operations
        decimal_values = [D(x) for x in values]
        decimal_mean = sum(decimal_values) / D(len(values))
        variance = sum((x - decimal_mean) ** D(2) for x in decimal_values) / D(len(decimal_values))

        return variance ** Decimal('0.5')  # Standard deviation

class UnifiedFairValueEngine:
    """
    Unified Fair-Value Engine

    Calculates fair value by blending oracle and AMM microprice:
    - Oracle ± AMM microprice blend based on confidence
    - Dynamic weighting based on market conditions
    - Confidence scoring for signal reliability
    """

    def __init__(
        self,
        base_oracle_weight: Decimal = Decimal('0.8'),    # 80% oracle weight by default
        min_oracle_weight: Decimal = Decimal('0.2'),     # Minimum oracle weight
        max_amm_weight: Decimal = Decimal('0.8'),        # Maximum AMM weight
        confidence_threshold: Decimal = Decimal('0.05'), # 5% confidence threshold
        adaptation_rate: Decimal = Decimal('0.1')        # How quickly to adapt weights
    ):
        self.base_oracle_weight = base_oracle_weight
        self.min_oracle_weight = min_oracle_weight
        self.max_amm_weight = max_amm_weight
        self.confidence_threshold = confidence_threshold
        self.adaptation_rate = adaptation_rate

        # State tracking
        self.last_fair_value = FairValueSignal(
            fair_price=Decimal('0'),
            oracle_weight=base_oracle_weight,
            amm_weight=Decimal('1') - base_oracle_weight,
            confidence_score=Decimal('0.5')
        )
        self.fair_value_history: List[FairValueSignal] = []

    async def calculate_unified_fair_value(
        self,
        oracle_price: Decimal,
        amm_microprice: Decimal,
        oracle_confidence: Decimal,
        market_regime: str = "normal",
        l2_orderbook: Optional[L2OrderBook] = None,
        additional_signals: Optional[Dict[str, Decimal]] = None
    ) -> FairValueSignal:
        """
        Calculate unified fair value blending oracle and AMM signals

        Args:
            oracle_price: Price from oracle
            amm_microprice: AMM microprice (mid between reserves)
            oracle_confidence: Oracle confidence score (0-1)
            market_regime: Current market regime
            l2_orderbook: L2 order book for additional signals
            additional_signals: Additional price signals

        Returns:
            FairValueSignal with blended price and metadata
        """
        # Calculate dynamic weights based on oracle confidence
        oracle_weight, amm_weight = self._calculate_dynamic_weights(
            oracle_confidence, market_regime
        )

        # Apply adaptation rate (gradual changes)
        oracle_weight = self.last_fair_value.oracle_weight * (Decimal('1') - self.adaptation_rate) + \
                       oracle_weight * self.adaptation_rate
        amm_weight = Decimal('1') - oracle_weight

        # Calculate blended fair price
        fair_price = (oracle_price * oracle_weight) + (amm_microprice * amm_weight)

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            oracle_confidence, oracle_price, amm_microprice, market_regime
        )

        # Additional signal processing
        signal_components = {
            "oracle_price": oracle_price,
            "amm_microprice": amm_microprice,
            "oracle_confidence": oracle_confidence,
            "price_divergence": abs(oracle_price - amm_microprice) / oracle_price,
            "regime": Decimal(str(hash(market_regime) % 1000)) / Decimal('1000')  # Simple regime encoding
        }

        if additional_signals:
            signal_components.update(additional_signals)

        # L2 order book signals
        if l2_orderbook:
            l2_signals = self._extract_l2_signals(l2_orderbook, fair_price)
            signal_components.update(l2_signals)

        # Create fair value signal
        fair_value = FairValueSignal(
            fair_price=fair_price,
            oracle_weight=oracle_weight,
            amm_weight=amm_weight,
            confidence_score=confidence_score,
            signal_components=signal_components
        )

        self.last_fair_value = fair_value
        self.fair_value_history.append(fair_value)
        if len(self.fair_value_history) > 100:  # Keep last 100 signals
            self.fair_value_history.pop(0)

        return fair_value

    def _calculate_dynamic_weights(
        self,
        oracle_confidence: Decimal,
        market_regime: str
    ) -> Tuple[Decimal, Decimal]:
        """Calculate dynamic weights based on confidence and regime"""
        # Base weight adjustment based on confidence
        if oracle_confidence > self.confidence_threshold:
            # High confidence - prefer oracle
            oracle_weight = self.base_oracle_weight
        else:
            # Low confidence - prefer AMM microprice
            confidence_factor = oracle_confidence / self.confidence_threshold
            oracle_weight = self.min_oracle_weight + \
                          (self.base_oracle_weight - self.min_oracle_weight) * confidence_factor

        # Market regime adjustments
        regime_multiplier = self._get_regime_weight_multiplier(market_regime)

        oracle_weight *= regime_multiplier
        oracle_weight = max(self.min_oracle_weight, min(oracle_weight, Decimal('1') - self.max_amm_weight))

        amm_weight = Decimal('1') - oracle_weight

        return oracle_weight, amm_weight

    def _get_regime_weight_multiplier(self, market_regime: str) -> Decimal:
        """Get weight multiplier based on market regime"""
        multipliers = {
            "calm": Decimal('1.0'),      # Normal weighting
            "normal": Decimal('1.0'),    # Normal weighting
            "volatile": Decimal('0.8'),  # Prefer AMM in volatile markets
            "toxic": Decimal('0.6')      # Strongly prefer AMM in toxic markets
        }
        return multipliers.get(market_regime, Decimal('1.0'))

    def _calculate_confidence_score(
        self,
        oracle_confidence: Decimal,
        oracle_price: Decimal,
        amm_microprice: Decimal,
        market_regime: str
    ) -> Decimal:
        """Calculate overall confidence score for fair value signal"""
        # Base confidence from oracle
        confidence = oracle_confidence

        # Price divergence penalty
        if oracle_price != 0:
            divergence = abs(oracle_price - amm_microprice) / oracle_price
            divergence_penalty = min(divergence * Decimal('2'), Decimal('0.5'))  # Max 50% penalty
            confidence *= (Decimal('1') - divergence_penalty)

        # Market regime adjustment
        regime_confidence = self._get_regime_confidence_multiplier(market_regime)
        confidence *= regime_confidence

        return confidence

    def _get_regime_confidence_multiplier(self, market_regime: str) -> Decimal:
        """Get confidence multiplier based on market regime"""
        multipliers = {
            "calm": Decimal('1.1'),      # Higher confidence in calm markets
            "normal": Decimal('1.0'),    # Normal confidence
            "volatile": Decimal('0.8'),  # Lower confidence in volatile markets
            "toxic": Decimal('0.6')      # Much lower confidence in toxic markets
        }
        return multipliers.get(market_regime, Decimal('1.0'))

    def _extract_l2_signals(self, l2_orderbook: L2OrderBook, fair_price: Decimal) -> Dict[str, Decimal]:
        """Extract signals from L2 order book"""
        signals = {}

        # Order book imbalance
        bid_depth = sum(level.size for level in l2_orderbook.bids[:5])
        ask_depth = sum(level.size for level in l2_orderbook.asks[:5])

        if bid_depth + ask_depth > 0:
            imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
            signals["l2_imbalance"] = imbalance

        # Spread signal
        if l2_orderbook.spread:
            spread_bps = l2_orderbook.spread_bps
            signals["l2_spread_bps"] = spread_bps or Decimal('0')

        # Mid price vs fair price divergence
        if l2_orderbook.mid_price:
            mid_divergence = (l2_orderbook.mid_price - fair_price) / fair_price
            signals["l2_mid_divergence"] = mid_divergence

        return signals

    def get_fair_value_statistics(self) -> Dict[str, Any]:
        """Get statistics about fair value calculations"""
        if not self.fair_value_history:
            return {"error": "No fair value history"}

        recent_signals = self.fair_value_history[-50:]  # Last 50 signals

        prices = [signal.fair_price for signal in recent_signals]
        confidences = [signal.confidence_score for signal in recent_signals]

        stats = {
            "total_signals": len(recent_signals),
            "current_fair_price": float(self.last_fair_value.fair_price),
            "current_confidence": float(self.last_fair_value.confidence_score),
            "avg_fair_price": float(sum(prices) / len(prices)),
            "avg_confidence": float(sum(confidences) / len(confidences)),
            "price_volatility": float(self._calculate_price_volatility(prices)),
            "confidence_volatility": float(self._calculate_volatility(confidences)),
            "oracle_weight_avg": float(sum(s.oracle_weight for s in recent_signals) / len(recent_signals)),
            "amm_weight_avg": float(sum(s.amm_weight for s in recent_signals) / len(recent_signals))
        }

        return stats

    def _calculate_price_volatility(self, prices: List[Decimal]) -> Decimal:
        """Calculate price volatility"""
        if len(prices) < 2:
            return Decimal('0')

        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)

        if not returns:
            return Decimal('0')

        # Calculate standard deviation of returns
        # Convert all returns to Decimal for consistent operations
        decimal_returns = [D(r) for r in returns]
        decimal_mean = sum(decimal_returns) / D(len(returns))
        variance = sum((r - decimal_mean) ** D(2) for r in decimal_returns) / D(len(decimal_returns))

        return variance ** Decimal('0.5')

    def _calculate_volatility(self, values: List[Decimal]) -> Decimal:
        """Calculate volatility of values"""
        if len(values) < 2:
            return Decimal('0')

        mean = sum(values) / D(len(values))
        variance = sum((D(x) - mean) ** D(2) for x in values) / D(len(values))

        return variance ** Decimal('0.5')

# Integrated Advanced Quote Engine
class AdvancedQuoteEngine:
    """
    Integrated Advanced Quote Engine

    Combines all advanced features:
    - Funding-skewed quote adaptation
    - Impact-aware inventory bands
    - Unified fair value calculation
    """

    def __init__(self):
        self.funding_adapter = FundingSkewedQuoteAdapter()
        self.inventory_bands = ImpactAwareInventoryBands()
        self.fair_value_engine = UnifiedFairValueEngine()

        # L2 integration
        self.l2_engine = L2OrderBookEngine()

        logger.info("AdvancedQuoteEngine initialized")

    async def calculate_advanced_quotes(
        self,
        perp_market: PerpMarket,
        current_inventory: Decimal,
        oracle_price: Decimal,
        funding_rate: Decimal,
        market_regime: str = "normal",
        use_l2_data: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive advanced quotes

        Args:
            perp_market: Drift PerpMarket instance
            current_inventory: Current inventory level (-1 to 1)
            oracle_price: Current oracle price
            funding_rate: Current funding rate
            market_regime: Current market regime
            use_l2_data: Whether to use L2 data for calculations

        Returns:
            Dictionary with all quote calculations and metadata
        """
        # Get L2 order book data if requested
        l2_orderbook = None
        if use_l2_data:
            try:
                l2_orderbook = await self.l2_engine.get_l2_orderbook(
                    market_name=perp_market.name,
                    depth=20,
                    include_oracle=True,
                    include_vamm=True
                )
            except Exception as e:
                logger.warning(f"Failed to get L2 data: {e}")

        # Calculate fair value
        amm_microprice = perp_market.amm.mark_price()
        fair_value = await self.fair_value_engine.calculate_unified_fair_value(
            oracle_price=oracle_price,
            amm_microprice=amm_microprice,
            oracle_confidence=perp_market.amm.last_oracle_conf_pct / PERCENTAGE_PRECISION,
            market_regime=market_regime,
            l2_orderbook=l2_orderbook
        )

        # Calculate funding-skewed adjustments
        funding_adjustment = self.funding_adapter.calculate_funding_skew_adjustment(
            funding_rate=funding_rate,
            position_imbalance=current_inventory,
            market_regime=market_regime
        )

        # Calculate impact-aware inventory bands
        inventory_band = await self.inventory_bands.calculate_impact_aware_bands(
            base_price=fair_value.fair_price,
            current_inventory=current_inventory,
            l2_orderbook=l2_orderbook,
            market_regime=market_regime
        )

        # Apply all adjustments to get final quotes
        base_bid_price = fair_value.fair_price * (Decimal('1') - inventory_band.band_width)
        base_ask_price = fair_value.fair_price * (Decimal('1') + inventory_band.band_width)

        # Apply funding adjustments
        final_bid_price = base_bid_price * (Decimal('1') - funding_adjustment.bid_spread_adjustment)
        final_ask_price = base_ask_price * (Decimal('1') + funding_adjustment.ask_spread_adjustment)

        # Ensure bid < ask
        if final_bid_price >= final_ask_price:
            mid_price = (final_bid_price + final_ask_price) / Decimal('2')
            spread = max(final_ask_price - final_bid_price, fair_value.fair_price * Decimal('0.0001'))
            final_bid_price = mid_price - spread / Decimal('2')
            final_ask_price = mid_price + spread / Decimal('2')

        result = {
            "quotes": {
                "bid_price": final_bid_price,
                "ask_price": final_ask_price,
                "mid_price": (final_bid_price + final_ask_price) / Decimal('2'),
                "spread_bps": ((final_ask_price - final_bid_price) / final_bid_price) * Decimal('10000')
            },
            "fair_value": {
                "price": fair_value.fair_price,
                "oracle_weight": fair_value.oracle_weight,
                "amm_weight": fair_value.amm_weight,
                "confidence_score": fair_value.confidence_score
            },
            "funding_adjustment": {
                "bid_spread_adjustment": funding_adjustment.bid_spread_adjustment,
                "ask_spread_adjustment": funding_adjustment.ask_spread_adjustment,
                "reason": funding_adjustment.reason
            },
            "inventory_band": {
                "bid_edge": inventory_band.bid_edge,
                "ask_edge": inventory_band.ask_edge,
                "band_width": inventory_band.band_width
            },
            "market_data": {
                "oracle_price": oracle_price,
                "amm_microprice": amm_microprice,
                "funding_rate": funding_rate,
                "market_regime": market_regime
            },
            "metadata": {
                "l2_data_used": l2_orderbook is not None,
                "timestamp": datetime.now().timestamp(),
                "confidence_score": fair_value.confidence_score
            }
        }

        return result

    def get_engine_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all engine components"""
        return {
            "funding_adapter": self.funding_adapter.get_adjustment_statistics(),
            "inventory_bands": self.inventory_bands.get_band_statistics(),
            "fair_value_engine": self.fair_value_engine.get_fair_value_statistics(),
            "overall_health": "operational"  # Could be enhanced with health checks
        }

# Convenience functions for external use
async def calculate_advanced_quotes(
    perp_market: PerpMarket,
    current_inventory: Decimal,
    oracle_price: Decimal,
    funding_rate: Decimal,
    market_regime: str = "normal"
) -> Dict[str, Any]:
    """Convenience function for advanced quote calculation"""
    engine = AdvancedQuoteEngine()
    return await engine.calculate_advanced_quotes(
        perp_market=perp_market,
        current_inventory=current_inventory,
        oracle_price=oracle_price,
        funding_rate=funding_rate,
        market_regime=market_regime
    )

def get_advanced_quote_engine_stats() -> Dict[str, Any]:
    """Get statistics from advanced quote engine"""
    engine = AdvancedQuoteEngine()
    return engine.get_engine_statistics()
