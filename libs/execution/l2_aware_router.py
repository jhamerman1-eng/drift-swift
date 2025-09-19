"""
L2-Aware Execution Router

Enhanced ExecutionRouter with comprehensive L2 order book awareness for intelligent
routing decisions, market microstructure analysis, and dynamic quote adjustment.

Key Features:
- L2 order book integration for routing decisions
- Market microstructure analysis for regime detection
- Dynamic quote adjustment based on liquidity depth
- Slippage estimation and market impact analysis
- Real-time liquidity monitoring
- Advanced risk management with L2 depth

Integration Points:
- L2OrderBookEngine for real-time market data
- TwapJitter for enhanced TWAP execution
- Compute budget optimization for efficient execution
- Multi-source liquidity aggregation
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass

from .router import ExecutionRouter, ExecIntent, OrderResult, ErrorType
from .twap_jitter import TwapJitter, TwapRegime
from ..orderbook.l2_orderbook_engine import (
    L2OrderBookEngine,
    L2OrderBook,
    analyze_market_regime,
    estimate_order_slippage
)
from ..configs.compute_budget_strategies import get_optimized_compute_budget

logger = logging.getLogger(__name__)

@dataclass
class LiquidityAnalysis:
    """Comprehensive liquidity analysis for routing decisions"""
    available_depth: Decimal
    slippage_estimate: Decimal
    market_impact: Decimal
    optimal_execution_size: Decimal
    recommended_strategy: str
    confidence_score: float

@dataclass
class L2RoutingDecision:
    """L2-aware routing decision with market analysis"""
    primary_driver: str  # "swift", "drift", "jit"
    fallback_driver: str
    execution_mode: str  # "aggressive", "conservative", "balanced"
    slice_size: Decimal
    priority_level: str
    market_regime: str
    liquidity_score: float
    reasoning: List[str]

class L2AwareExecutionRouter(ExecutionRouter):
    """
    L2-Aware Execution Router with Advanced Market Analysis

    Extends ExecutionRouter with comprehensive L2 order book awareness,
    enabling intelligent routing decisions based on real-time market conditions.
    """

    def __init__(
        self,
        drift_client,
        swift_client=None,
        l2_engine: Optional[L2OrderBookEngine] = None,
        twap_engine: Optional[TwapJitter] = None,
        market_name: str = "SOL-PERP",  # Default market
        l2_update_interval: float = 1.0,  # Update L2 every second
        slippage_tolerance_bps: Decimal = Decimal('50'),  # 0.5% slippage tolerance
        **kwargs
    ):
        # Initialize parent ExecutionRouter
        super().__init__(
            drift_client=drift_client,
            swift_client=swift_client,
            **kwargs
        )

        # L2 order book integration
        self.l2_engine = l2_engine or L2OrderBookEngine()
        self.market_name = market_name
        self.l2_update_interval = l2_update_interval
        self.slippage_tolerance_bps = slippage_tolerance_bps

        # TWAP integration
        self.twap_engine = twap_engine

        # L2 data cache
        self._current_l2_orderbook: Optional[L2OrderBook] = None
        self._last_l2_update: float = 0
        self._l2_update_task: Optional[asyncio.Task] = None

        # Market analysis cache
        self._market_regime: Optional[TwapRegime] = None
        self._liquidity_analysis: Optional[LiquidityAnalysis] = None

        logger.info(f"L2AwareExecutionRouter initialized for {market_name}")

    async def initialize(self):
        """Initialize L2 data streams and background tasks"""
        await super().initialize()

        # Initialize L2 engine
        await self.l2_engine.initialize()

        # Start L2 update task
        self._l2_update_task = asyncio.create_task(self._l2_update_loop())

        logger.info("L2AwareExecutionRouter fully initialized")

    async def close(self):
        """Clean shutdown with L2 data streams"""
        # Stop L2 update task
        if self._l2_update_task:
            self._l2_update_task.cancel()
            try:
                await self._l2_update_task
            except asyncio.CancelledError:
                pass

        # Close L2 engine
        await self.l2_engine.close()

        await super().close()

    async def _l2_update_loop(self):
        """Background task to maintain fresh L2 data"""
        while True:
            try:
                await self._update_l2_data()
                await asyncio.sleep(self.l2_update_interval)
            except Exception as e:
                logger.error(f"L2 update loop error: {e}")
                await asyncio.sleep(self.l2_update_interval)

    async def _update_l2_data(self):
        """Fetch and analyze fresh L2 order book data"""
        try:
            # Fetch latest L2 order book
            orderbook = await self.l2_engine.get_l2_orderbook(
                market_name=self.market_name,
                depth=20,
                include_oracle=True,
                include_vamm=True
            )

            if orderbook:
                self._current_l2_orderbook = orderbook
                self._last_l2_update = asyncio.get_event_loop().time()

                # Update market analysis
                await self._update_market_analysis()

        except Exception as e:
            logger.error(f"Failed to update L2 data: {e}")

    async def _update_market_analysis(self):
        """Update market regime and liquidity analysis"""
        if not self._current_l2_orderbook:
            return

        # Analyze market regime
        regime_analysis = analyze_market_regime(self._current_l2_orderbook)
        self._market_regime = TwapRegime(regime_analysis['regime'])

        # Perform liquidity analysis
        self._liquidity_analysis = await self._analyze_liquidity()

    async def _analyze_liquidity(self) -> LiquidityAnalysis:
        """Perform comprehensive liquidity analysis"""
        if not self._current_l2_orderbook:
            return LiquidityAnalysis(
                available_depth=Decimal('0'),
                slippage_estimate=Decimal('0'),
                market_impact=Decimal('0'),
                optimal_execution_size=Decimal('0'),
                recommended_strategy="unknown",
                confidence_score=0.0
            )

        # Calculate available depth (top 5 levels)
        bid_depth = sum(level.size for level in self._current_l2_orderbook.bids[:5])
        ask_depth = sum(level.size for level in self._current_l2_orderbook.asks[:5])
        available_depth = min(bid_depth, ask_depth)

        # Estimate slippage for typical order sizes
        test_sizes = [
            available_depth * Decimal('0.01'),  # 1% of available depth
            available_depth * Decimal('0.05'),  # 5% of available depth
            available_depth * Decimal('0.10'),  # 10% of available depth
        ]

        slippage_estimates = []
        for size in test_sizes:
            bid_slippage = estimate_order_slippage(self._current_l2_orderbook, size, 'bid')
            ask_slippage = estimate_order_slippage(self._current_l2_orderbook, size, 'ask')
            avg_slippage = (abs(bid_slippage.get('slippage_bps', 0)) +
                          abs(ask_slippage.get('slippage_bps', 0))) / 2
            slippage_estimates.append(avg_slippage)

        avg_slippage = sum(slippage_estimates) / len(slippage_estimates)

        # Market impact assessment
        market_impact = avg_slippage * 2  # Simplified impact calculation

        # Optimal execution size (don't consume more than 5% of available depth)
        optimal_execution_size = available_depth * Decimal('0.05')

        # Strategy recommendation
        if avg_slippage < 10:  # Low slippage (< 0.1%)
            recommended_strategy = "aggressive"
        elif avg_slippage < 50:  # Moderate slippage (< 0.5%)
            recommended_strategy = "balanced"
        else:  # High slippage
            recommended_strategy = "conservative"

        # Confidence score based on data freshness and depth
        confidence_score = min(1.0, available_depth / Decimal('1000000'))  # Scale by 1M units

        return LiquidityAnalysis(
            available_depth=available_depth,
            slippage_estimate=Decimal(str(avg_slippage)),
            market_impact=Decimal(str(market_impact)),
            optimal_execution_size=optimal_execution_size,
            recommended_strategy=recommended_strategy,
            confidence_score=confidence_score
        )

    def make_l2_aware_routing_decision(
        self,
        order_params: Dict[str, Any],
        intent: ExecIntent,
        context: str = ""
    ) -> L2RoutingDecision:
        """
        Make intelligent routing decision based on L2 order book analysis

        Args:
            order_params: Order parameters
            intent: Execution intent
            context: Order context for decision making

        Returns:
            L2-aware routing decision
        """
        reasoning = []

        # Default decision
        decision = L2RoutingDecision(
            primary_driver="drift",
            fallback_driver="drift",
            execution_mode="balanced",
            slice_size=Decimal('0'),
            priority_level="medium",
            market_regime="unknown",
            liquidity_score=0.5,
            reasoning=[]
        )

        # Check L2 data availability
        if not self._current_l2_orderbook or not self._liquidity_analysis:
            reasoning.append("L2 data unavailable, using default routing")
            decision.reasoning = reasoning
            return decision

        # Market regime analysis
        market_regime = self._market_regime or TwapRegime.CALM
        decision.market_regime = market_regime.value
        reasoning.append(f"Market regime: {market_regime.value}")

        # Liquidity analysis
        liquidity = self._liquidity_analysis
        decision.liquidity_score = liquidity.confidence_score

        if liquidity.confidence_score < 0.3:
            reasoning.append("Low liquidity confidence, conservative routing")
            decision.primary_driver = "drift"
            decision.execution_mode = "conservative"
        elif liquidity.confidence_score > 0.7:
            reasoning.append("High liquidity confidence, can use aggressive routing")
            decision.primary_driver = "swift"
            decision.execution_mode = "aggressive"

        # Intent-specific routing
        if intent == ExecIntent.TAKER:
            if self._current_l2_orderbook.spread_bps and self._current_l2_orderbook.spread_bps < 5:
                decision.primary_driver = "swift"  # Tight spread, use Swift
                reasoning.append("Tight spread detected, routing to Swift for best execution")
            else:
                decision.primary_driver = "drift"  # Wide spread, use Drift
                reasoning.append("Wide spread detected, using Drift for reliability")

        elif intent == ExecIntent.MAKER:
            decision.primary_driver = "drift"  # Always use Drift for maker orders
            decision.execution_mode = "conservative"
            reasoning.append("Maker order, using Drift for post-only execution")

        elif intent == ExecIntent.TWAP:
            # TWAP-specific logic based on regime
            if market_regime == TwapRegime.VOLATILE:
                decision.primary_driver = "drift"
                decision.execution_mode = "conservative"
                reasoning.append("Volatile market, TWAP using conservative Drift execution")
            elif market_regime == TwapRegime.CALM:
                decision.primary_driver = "swift"
                decision.execution_mode = "balanced"
                reasoning.append("Calm market, TWAP using balanced Swift execution")
            else:  # TOXIC
                decision.primary_driver = "drift"
                decision.execution_mode = "conservative"
                reasoning.append("Toxic market, TWAP paused or very conservative")

        # Compute budget optimization
        order_size = Decimal(str(order_params.get('base_asset_amount', 1)))
        compute_budget = get_optimized_compute_budget(
            strategy="twap" if intent == ExecIntent.TWAP else "dex_trade",
            market_condition=market_regime.value,
            priority_level=decision.execution_mode
        )

        decision.priority_level = compute_budget.get('priority_level', 'medium')

        # Slice size optimization for TWAP
        if intent == ExecIntent.TWAP and self.twap_engine:
            slice_recommendation = self.twap_engine._l2_engine.calculate_optimal_slice_size(
                self._current_l2_orderbook,
                order_size,
                'bid'  # Assume bid for TWAP
            )
            decision.slice_size = slice_recommendation['optimal_slice_size']
            reasoning.append(f"Optimal TWAP slice size: {decision.slice_size}")

        decision.reasoning = reasoning
        return decision

    async def place_with_l2_awareness(
        self,
        order_params: Dict[str, Any],
        intent: ExecIntent,
        context: str = "",
        **kwargs
    ) -> OrderResult:
        """
        Enhanced order placement with L2 awareness

        Args:
            order_params: Order parameters
            intent: Execution intent
            context: Order context
            **kwargs: Additional parameters

        Returns:
            OrderResult with L2-aware execution
        """
        # Get L2-aware routing decision
        routing_decision = self.make_l2_aware_routing_decision(order_params, intent, context)

        # Log routing decision
        logger.info(f"L2-aware routing decision: {routing_decision.primary_driver} "
                   f"({routing_decision.execution_mode}) - {routing_decision.market_regime}")

        # Apply compute budget optimization
        enhanced_params = self._prepare_swift_order_with_compute_budget(
            order_params,
            order_type="twap" if intent == ExecIntent.TWAP else "dex_trade"
        )

        # Apply routing decision
        if routing_decision.primary_driver == "swift" and self.swift_enabled:
            enhanced_params['priority_level'] = routing_decision.priority_level
        elif routing_decision.execution_mode == "conservative":
            # Force more conservative execution
            enhanced_params['compute_unit_price'] = max(
                enhanced_params.get('compute_unit_price', 10000) // 2,
                1000  # Minimum price
            )

        # Execute order with enhanced parameters
        return await self.place(
            order_params=enhanced_params,
            intent=intent,
            context=f"{context}_l2_aware_{routing_decision.execution_mode}",
            **kwargs
        )

    def get_l2_market_analysis(self) -> Dict[str, Any]:
        """Get comprehensive L2 market analysis"""
        if not self._current_l2_orderbook:
            return {"error": "L2 data not available"}

        analysis = {
            "market_name": self.market_name,
            "last_update": self._last_l2_update,
            "market_regime": self._market_regime.value if self._market_regime else "unknown",
            "spread_bps": float(self._current_l2_orderbook.spread_bps) if self._current_l2_orderbook.spread_bps else None,
            "mid_price": float(self._current_l2_orderbook.mid_price) if self._current_l2_orderbook.mid_price else None,
            "oracle_price": float(self._current_l2_orderbook.oracle_price) if self._current_l2_orderbook.oracle_price else None
        }

        if self._liquidity_analysis:
            analysis.update({
                "liquidity_analysis": {
                    "available_depth": float(self._liquidity_analysis.available_depth),
                    "slippage_estimate_bps": float(self._liquidity_analysis.slippage_estimate),
                    "market_impact_bps": float(self._liquidity_analysis.market_impact),
                    "optimal_execution_size": float(self._liquidity_analysis.optimal_execution_size),
                    "recommended_strategy": self._liquidity_analysis.recommended_strategy,
                    "confidence_score": self._liquidity_analysis.confidence_score
                }
            })

        return analysis

    def get_l2_routing_recommendations(self) -> Dict[str, Any]:
        """Get L2-based routing recommendations"""
        if not self._current_l2_orderbook or not self._liquidity_analysis:
            return {"error": "Insufficient L2 data for recommendations"}

        recommendations = {
            "market_conditions": {
                "regime": self._market_regime.value if self._market_regime else "unknown",
                "liquidity_score": self._liquidity_analysis.confidence_score,
                "spread_bps": float(self._current_l2_orderbook.spread_bps) if self._current_l2_orderbook.spread_bps else None
            },
            "routing_recommendations": {
                "maker_orders": {
                    "preferred_driver": "drift",
                    "reasoning": "Always use Drift for post-only maker orders"
                },
                "taker_orders": {
                    "preferred_driver": "swift" if self._liquidity_analysis.confidence_score > 0.7 else "drift",
                    "reasoning": f"High liquidity confidence ({self._liquidity_analysis.confidence_score:.2f})" if self._liquidity_analysis.confidence_score > 0.7 else "Moderate liquidity, using Drift for reliability"
                },
                "twap_orders": {
                    "preferred_driver": "swift" if self._market_regime == TwapRegime.CALM else "drift",
                    "execution_mode": "conservative" if self._market_regime == TwapRegime.TOXIC else "balanced",
                    "reasoning": f"TWAP in {self._market_regime.value} regime"
                }
            },
            "risk_assessment": {
                "slippage_risk": "low" if self._liquidity_analysis.slippage_estimate < 25 else "high",
                "market_impact": "low" if self._liquidity_analysis.market_impact < 50 else "high",
                "recommended_position_size": float(self._liquidity_analysis.optimal_execution_size)
            }
        }

        return recommendations

# Convenience functions for external use
async def create_l2_aware_router(
    drift_client,
    swift_client=None,
    market_name: str = "SOL-PERP",
    **kwargs
) -> L2AwareExecutionRouter:
    """Create and initialize L2-aware execution router"""
    router = L2AwareExecutionRouter(
        drift_client=drift_client,
        swift_client=swift_client,
        market_name=market_name,
        **kwargs
    )
    await router.initialize()
    return router

def get_l2_market_insights(orderbook: L2OrderBook) -> Dict[str, Any]:
    """Get market microstructure insights from L2 order book"""
    engine = L2OrderBookEngine()
    metrics = engine.analyze_market_microstructure(orderbook)

    return {
        "spread_analysis": {
            "spread_bps": float(metrics.spread_bps) if metrics.spread_bps else None,
            "spread_category": "tight" if (metrics.spread_bps and metrics.spread_bps < 10) else "wide"
        },
        "depth_analysis": {
            "depth_imbalance": float(metrics.depth_imbalance),
            "volume_profile": metrics.volume_profile
        },
        "market_regime": {
            "volatility_regime": metrics.volatility_regime,
            "market_resilience": metrics.market_resilience,
            "detected_regime": engine.detect_market_regime(orderbook).value
        }
    }


