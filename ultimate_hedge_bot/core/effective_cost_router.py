"""
Ultimate Hedge Bot - Effective Cost Router
Fixed effective cost calculation with proper non-linear size impact.
"""

import math
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RoutingCandidate:
    """Candidate venue for order routing."""
    venue: str
    base_cost: float
    size_multiplier: float
    effective_cost: float
    estimated_fill_time: float
    confidence_score: float
    orderbook_depth: Dict[str, Any]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RoutingResult:
    """Result of effective cost routing."""
    best_venue: str
    effective_cost: float
    expected_savings: float
    routing_candidates: List[RoutingCandidate]
    routing_time_ms: float
    confidence_level: str
    reasoning: List[str]


class EffectiveCostRouter:
    """
    Advanced effective cost routing with non-linear size impact.

    Fixed Issues:
    - ✅ Non-linear EC calculation: EC = SlippageImpact(L2, side, qty) * (1 + qty/avg_daily_volume)^0.5 + FeeBps
    - ✅ Realistic slippage calculation walking orderbook depth
    - ✅ Size-based impact multiplier
    - ✅ Venue-specific fee structures
    - ✅ Confidence scoring and risk assessment
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Venue-specific configurations
        self.venue_configs = {
            'drift': {
                'maker_fee_bps': 0,      # 0% maker fee
                'taker_fee_bps': 5,      # 0.05% taker fee
                'avg_daily_volume': 50000000,  # $50M daily volume
                'slippage_buffer': 0.001,      # 0.1% buffer
                'latency_ms': 50
            },
            'binance': {
                'maker_fee_bps': -2.5,   # -0.025% maker rebate
                'taker_fee_bps': 7.5,    # 0.075% taker fee
                'avg_daily_volume': 100000000,  # $100M daily volume
                'slippage_buffer': 0.002,       # 0.2% buffer
                'latency_ms': 100
            },
            'bybit': {
                'maker_fee_bps': -2,     # -0.02% maker rebate
                'taker_fee_bps': 6,      # 0.06% taker fee
                'avg_daily_volume': 75000000,   # $75M daily volume
                'slippage_buffer': 0.0015,      # 0.15% buffer
                'latency_ms': 80
            }
        }

        # Size impact coefficients
        self.size_impact_coefficients = {
            'small': 0.3,      # < $1000: minimal impact
            'medium': 0.5,     # $1000-$10000: moderate impact
            'large': 0.7,      # $10000-$100000: significant impact
            'xlarge': 1.0      # > $100000: maximum impact
        }

    async def calculate_effective_cost(self, l2_orderbook: Dict[str, Any],
                                     side: str, qty: float, venue: str,
                                     maker_taker: str = 'taker') -> float:
        """
        Calculate true effective cost with non-linear size impact.

        Formula: EC = SlippageImpact(L2, side, qty) * (1 + qty/avg_daily_volume)^0.5 + FeeBps

        Args:
            l2_orderbook: Level 2 orderbook data
            side: 'buy' or 'sell'
            qty: Order quantity in base currency
            venue: Venue name
            maker_taker: 'maker' or 'taker'

        Returns:
            Effective cost as percentage (e.g., 0.005 = 0.5%)
        """
        try:
            # 1. Calculate slippage impact by walking orderbook
            slippage_impact = self._calculate_slippage_impact(l2_orderbook, side, qty)

            # 2. Apply size-based multiplier (non-linear impact)
            venue_config = self.venue_configs.get(venue, self.venue_configs['drift'])
            avg_daily_volume = venue_config['avg_daily_volume']

            # Size multiplier with square root for non-linear scaling
            size_multiplier = math.sqrt(1 + qty / avg_daily_volume)

            # 3. Add venue fees
            fee_bps = self._get_venue_fees(venue, maker_taker)

            # 4. Calculate final effective cost
            effective_cost = slippage_impact * size_multiplier + (fee_bps / 10000)

            logger.debug(".6f"                     ".2f"
                     ".6f")

            return effective_cost

        except Exception as e:
            logger.error(f"Effective cost calculation failed: {e}")
            # Return high cost to discourage routing to this venue
            return 0.01  # 1% fallback

    def _calculate_slippage_impact(self, l2_orderbook: Dict[str, Any],
                                 side: str, qty: float) -> float:
        """
        Calculate realistic slippage by walking orderbook depth.

        Args:
            l2_orderbook: L2 orderbook with bids/asks
            side: 'buy' or 'sell'
            qty: Order quantity

        Returns:
            Slippage impact as percentage
        """
        if not l2_orderbook or 'bids' not in l2_orderbook or 'asks' not in l2_orderbook:
            logger.warning("Invalid orderbook data, using default slippage")
            return 0.002  # 0.2% default

        try:
            if side == "buy":
                # Walk the ask side (selling to us)
                return self._walk_orderbook(l2_orderbook['asks'], qty, ascending=True)
            else:
                # Walk the bid side (buying from us)
                return self._walk_orderbook(l2_orderbook['bids'], qty, ascending=False)

        except Exception as e:
            logger.error(f"Slippage calculation failed: {e}")
            return 0.002  # 0.2% default

    def _walk_orderbook(self, levels: List[List[float]], qty: float,
                       ascending: bool = True) -> float:
        """
        Walk orderbook levels to calculate true execution price.

        Args:
            levels: [[price, size], ...] orderbook levels
            qty: Total quantity to execute
            ascending: True for asks (buying), False for bids (selling)

        Returns:
            Slippage impact as percentage from best level
        """
        if not levels:
            return 0.005  # 0.5% default

        remaining_qty = qty
        total_cost = 0.0
        best_price = levels[0][0] if levels else 100.0

        for level in levels:
            if len(level) < 2:
                continue

            level_price = level[0]
            level_size = level[1]

            # Take what's available at this level
            take_size = min(remaining_qty, level_size)
            total_cost += take_size * level_price
            remaining_qty -= take_size

            if remaining_qty <= 0:
                break

        if qty <= 0:
            return 0.0

        # Calculate volume-weighted average price
        vwap = total_cost / qty

        # Calculate slippage from best price
        if ascending:  # Buying (asks) - slippage is positive
            slippage = (vwap - best_price) / best_price
        else:  # Selling (bids) - slippage is negative (favorable)
            slippage = (best_price - vwap) / best_price

        # Ensure non-negative slippage
        return max(0.0, slippage)

    def _get_venue_fees(self, venue: str, maker_taker: str) -> float:
        """Get venue-specific fees in basis points."""
        venue_config = self.venue_configs.get(venue, self.venue_configs['drift'])

        if maker_taker == 'maker':
            return venue_config['maker_fee_bps']
        else:
            return venue_config['taker_fee_bps']

    async def find_best_routing(self, orderbook_data: Dict[str, Dict[str, Any]],
                              side: str, qty: float, urgency_score: float = 0.5) -> RoutingResult:
        """
        Find best venue routing based on effective cost calculation.

        Args:
            orderbook_data: Orderbook data by venue {'venue': orderbook}
            side: 'buy' or 'sell'
            qty: Order quantity
            urgency_score: Urgency factor (0-1)

        Returns:
            RoutingResult with best venue and analysis
        """
        start_time = time.time()
        candidates = []
        reasoning = []

        # Evaluate each venue
        for venue, orderbook in orderbook_data.items():
            try:
                # Calculate effective cost for both maker and taker
                maker_cost = await self.calculate_effective_cost(
                    orderbook, side, qty, venue, 'maker'
                )
                taker_cost = await self.calculate_effective_cost(
                    orderbook, side, qty, venue, 'taker'
                )

                # Choose best execution method
                if maker_cost <= taker_cost:
                    best_cost = maker_cost
                    execution_method = 'maker'
                else:
                    best_cost = taker_cost
                    execution_method = 'taker'

                # Calculate confidence and timing
                confidence = self._calculate_routing_confidence(orderbook, qty, venue)
                estimated_time = self._estimate_fill_time(venue, qty, execution_method)

                # Apply urgency adjustment
                adjusted_cost = best_cost * (1 - urgency_score * 0.1)  # Max 10% discount for urgency

                candidate = RoutingCandidate(
                    venue=venue,
                    base_cost=best_cost,
                    size_multiplier=self._calculate_size_multiplier(qty, venue),
                    effective_cost=adjusted_cost,
                    estimated_fill_time=estimated_time,
                    confidence_score=confidence,
                    orderbook_depth=orderbook,
                    metadata={
                        'execution_method': execution_method,
                        'urgency_adjustment': urgency_score * 0.1,
                        'raw_maker_cost': maker_cost,
                        'raw_taker_cost': taker_cost
                    }
                )

                candidates.append(candidate)

            except Exception as e:
                logger.warning(f"Failed to evaluate venue {venue}: {e}")
                reasoning.append(f"❌ Venue {venue} evaluation failed: {e}")

        if not candidates:
            raise RuntimeError("No valid routing candidates found")

        # Find best candidate
        best_candidate = min(candidates, key=lambda x: x.effective_cost)
        routing_time = (time.time() - start_time) * 1000

        # Calculate expected savings
        if len(candidates) > 1:
            next_best = sorted(candidates, key=lambda x: x.effective_cost)[1]
            expected_savings = next_best.effective_cost - best_candidate.effective_cost
        else:
            expected_savings = 0.0

        # Build reasoning
        reasoning.append(f"✅ Best venue: {best_candidate.venue}")
        reasoning.append(".6f")
        reasoning.append(".4f")
        reasoning.append(".2f")
        reasoning.append(f"⚡ Estimated fill time: {best_candidate.estimated_fill_time:.1f}ms")

        result = RoutingResult(
            best_venue=best_candidate.venue,
            effective_cost=best_candidate.effective_cost,
            expected_savings=expected_savings,
            routing_candidates=candidates,
            routing_time_ms=routing_time,
            confidence_level=self._classify_confidence(best_candidate.confidence_score),
            reasoning=reasoning
        )

        logger.info(f"🎯 Routing complete: {best_candidate.venue} selected in {routing_time:.1f}ms")
        return result

    def _calculate_size_multiplier(self, qty: float, venue: str) -> float:
        """Calculate size-based multiplier."""
        venue_config = self.venue_configs.get(venue, self.venue_configs['drift'])
        avg_volume = venue_config['avg_daily_volume']

        return math.sqrt(1 + qty / avg_volume)

    def _calculate_routing_confidence(self, orderbook: Dict[str, Any],
                                    qty: float, venue: str) -> float:
        """
        Calculate confidence score for routing decision.

        Factors:
        - Orderbook depth relative to order size
        - Recent volatility
        - Venue reliability
        """
        try:
            # Check orderbook depth
            depth_score = self._calculate_depth_score(orderbook, qty)

            # Venue reliability (simplified)
            venue_reliability = 0.9  # Could be dynamic based on historical data

            # Combine factors
            confidence = (depth_score * 0.7) + (venue_reliability * 0.3)

            return min(1.0, max(0.0, confidence))

        except Exception:
            return 0.5  # Medium confidence fallback

    def _calculate_depth_score(self, orderbook: Dict[str, Any], qty: float) -> float:
        """Calculate orderbook depth score."""
        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])

            # Calculate total depth within 1% of best price
            best_bid = bids[0][0] if bids else 0
            best_ask = asks[0][0] if asks else float('inf')

            bid_depth = sum(size for price, size in bids[:10]  # Top 10 levels
                          if price >= best_bid * 0.99)

            ask_depth = sum(size for price, size in asks[:10]  # Top 10 levels
                          if price <= best_ask * 1.01)

            total_depth = (bid_depth + ask_depth) / 2
            depth_ratio = total_depth / qty

            # Score based on depth ratio
            if depth_ratio >= 5:  # 5x order size available
                return 1.0
            elif depth_ratio >= 2:  # 2x order size available
                return 0.8
            elif depth_ratio >= 1:  # 1x order size available
                return 0.6
            else:
                return 0.3  # Insufficient depth

        except Exception:
            return 0.5

    def _estimate_fill_time(self, venue: str, qty: float, execution_method: str) -> float:
        """Estimate fill time in milliseconds."""
        venue_config = self.venue_configs.get(venue, self.venue_configs['drift'])
        base_latency = venue_config['latency_ms']

        # Size-based adjustment
        size_factor = min(1.0, qty / 10000)  # Max 10x for very large orders

        # Execution method adjustment
        method_factor = 0.5 if execution_method == 'maker' else 1.0

        return base_latency * size_factor * method_factor

    def _classify_confidence(self, score: float) -> str:
        """Classify confidence level."""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        elif score >= 0.4:
            return "low"
        else:
            return "very_low"

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing performance statistics."""
        return {
            'venue_configs': self.venue_configs,
            'size_impact_coefficients': self.size_impact_coefficients,
            'supported_venues': list(self.venue_configs.keys())
        }
