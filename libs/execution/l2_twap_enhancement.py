"""
L2 Order Book Enhanced TWAP Execution

Integrates real-time L2 order book data with TWAP execution for optimal
slice sizing, regime detection, and market impact minimization.

Key Features:
- L2 depth analysis for intelligent slice sizing
- Market regime detection using spread and liquidity metrics
- Slippage estimation and market impact assessment
- Dynamic TWAP parameter adjustment based on market conditions
- Risk-aware execution with liquidity monitoring
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from .twap_jitter import TwapJitter, TwapExecutionState, TwapIntent, TwapExecutionMode, TwapRegime
from ..market_data.l2_orderbook_client import (
    l2_client,
    L2OrderBook,
    MarketDepthAnalysis,
    DriftL2OrderBookClient
)
from ..configs.compute_budget_strategies import TradingStrategy, MarketCondition

logger = logging.getLogger(__name__)

@dataclass
class L2MarketMetrics:
    """Real-time market metrics derived from L2 order book data"""
    spread_bps: float
    bid_depth: Decimal
    ask_depth: Decimal
    imbalance_ratio: float
    concentration_score: float
    slippage_estimate_buy: float
    slippage_estimate_sell: float
    liquidity_score: float
    volatility_indicator: float
    timestamp: float = field(default_factory=time.time)

@dataclass
class L2TwapExecutionConfig:
    """Enhanced TWAP configuration with L2 awareness"""
    market_name: str
    base_twap_config: Dict[str, Any]
    l2_depth_levels: int = 5
    max_slippage_bps: float = 50.0
    liquidity_threshold: float = 1000000  # Minimum liquidity in base units
    volatility_adjustment: bool = True
    adaptive_sizing: bool = True
    regime_detection_enabled: bool = True

class L2AwareTwapExecution(TwapJitter):
    """
    L2 Order Book Aware TWAP Execution Engine

    Enhances traditional TWAP execution with real-time market data analysis
    for optimal slice sizing, regime detection, and risk management.
    """

    def __init__(
        self,
        drift_client,
        swift_client=None,
        l2_client: Optional[DriftL2OrderBookClient] = None,
        market_name: str = "",
        regime_classifier: Optional[Callable[[], TwapRegime]] = None,
        toxicity_filter: Optional[Callable[[], bool]] = None,
        **kwargs
    ):
        super().__init__(
            drift_client=drift_client,
            swift_client=swift_client,
            regime_classifier=regime_classifier,
            toxicity_filter=toxicity_filter,
            **kwargs
        )

        # L2 order book integration
        self.l2_client = l2_client or l2_orderbook_client
        self.market_name = market_name

        # L2 market monitoring
        self.current_market_metrics: Optional[L2MarketMetrics] = None
        self.market_monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None

        # Enhanced TWAP configurations
        self.l2_configs: Dict[str, L2TwapExecutionConfig] = {}

        # Market data cache
        self._market_data_cache: Dict[str, Any] = {}
        self._cache_ttl = 0.5  # 500ms cache for fast-moving data

        logger.info(f"Initialized L2-Aware TWAP Execution for {market_name}")

    async def start_l2_twap_execution(
        self,
        execution_id: str,
        current_position: Decimal,
        target_position: Decimal,
        duration_sec: int,
        market_name: str,
        l2_config: Optional[L2TwapExecutionConfig] = None,
        **kwargs
    ) -> bool:
        """
        Start L2-aware TWAP execution with market analysis

        Args:
            execution_id: Unique execution identifier
            current_position: Starting position
            target_position: Target position
            duration_sec: Total execution duration
            market_name: Market to monitor for L2 data
            l2_config: L2-specific TWAP configuration
            **kwargs: Additional TWAP parameters

        Returns:
            True if execution started successfully
        """
        # Set default L2 configuration
        if l2_config is None:
            l2_config = L2TwapExecutionConfig(
                market_name=market_name,
                base_twap_config=kwargs
            )

        self.l2_configs[execution_id] = l2_config
        self.market_name = market_name

        # Start market monitoring if not already active
        if not self.market_monitoring_active:
            await self.start_market_monitoring()

        # Start base TWAP execution
        success = await self.start_twap_execution(
            execution_id=execution_id,
            current_position=current_position,
            target_position=target_position,
            duration_sec=duration_sec,
            **kwargs
        )

        if success:
            logger.info(f"Started L2-aware TWAP execution {execution_id} for {market_name}")

        return success

    async def start_market_monitoring(self):
        """Start real-time market monitoring for L2 data"""
        if self.market_monitoring_active:
            return

        self.market_monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._market_monitoring_loop())

        logger.info("Started L2 market monitoring")

    async def stop_market_monitoring(self):
        """Stop market monitoring"""
        self.market_monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None

        logger.info("Stopped L2 market monitoring")

    async def _market_monitoring_loop(self):
        """Continuous market monitoring loop"""
        while self.market_monitoring_active:
            try:
                await self._update_market_metrics()
                await asyncio.sleep(0.5)  # 2Hz monitoring
            except Exception as e:
                logger.error(f"Market monitoring error: {e}")
                await asyncio.sleep(1.0)

    async def _update_market_metrics(self):
        """Update current market metrics from L2 data"""
        if not self.market_name:
            return

        try:
            # Get L2 order book
            orderbook = await self.l2_client.get_l2_orderbook(
                self.market_name,
                depth=20,
                use_cache=False  # Always get fresh data for monitoring
            )

            if not orderbook:
                return

            # Analyze market depth
            analysis = self.l2_client.analyze_market_depth(orderbook, depth_levels=5)

            # Estimate slippage
            slippage_buy = self.l2_client.estimate_slippage(
                orderbook, Decimal('1000000'), is_buy=True
            )
            slippage_sell = self.l2_client.estimate_slippage(
                orderbook, Decimal('1000000'), is_buy=False
            )

            # Calculate additional metrics
            liquidity_score = self._calculate_liquidity_score(orderbook)
            volatility_indicator = self._calculate_volatility_indicator(orderbook)

            # Update current metrics
            self.current_market_metrics = L2MarketMetrics(
                spread_bps=analysis.spread_bps,
                bid_depth=analysis.bid_depth,
                ask_depth=analysis.ask_depth,
                imbalance_ratio=analysis.imbalance_ratio,
                concentration_score=analysis.concentration_score,
                slippage_estimate_buy=slippage_buy['slippage_bps'],
                slippage_estimate_sell=slippage_sell['slippage_bps'],
                liquidity_score=liquidity_score,
                volatility_indicator=volatility_indicator
            )

        except Exception as e:
            logger.error(f"Failed to update market metrics: {e}")

    def _calculate_liquidity_score(self, orderbook: L2OrderBook) -> float:
        """Calculate liquidity score based on order book depth"""
        if not orderbook.bids or not orderbook.asks:
            return 0.0

        # Calculate total liquidity in top 10 levels
        total_bid_liquidity = sum(level.size for level in orderbook.bids[:10])
        total_ask_liquidity = sum(level.size for level in orderbook.asks[:10])
        total_liquidity = total_bid_liquidity + total_ask_liquidity

        # Normalize by typical order size (arbitrary scale)
        base_score = float(total_liquidity / Decimal('10000000'))  # 10M base units as baseline

        # Cap at reasonable range
        return min(max(base_score, 0.1), 5.0)

    def _calculate_volatility_indicator(self, orderbook: L2OrderBook) -> float:
        """Calculate volatility indicator from spread and depth"""
        if not self.current_market_metrics:
            return 0.0

        # Combine spread and concentration as volatility proxy
        spread_factor = self.current_market_metrics.spread_bps / 100.0  # Normalize spread
        concentration_factor = self.current_market_metrics.concentration_score / 100.0

        # Higher concentration + wider spread = higher volatility
        volatility = (spread_factor * 0.7) + (concentration_factor * 0.3)

        return min(volatility, 1.0)  # Cap at 1.0

    def detect_regime_with_l2(self, orderbook: Optional[L2OrderBook] = None) -> TwapRegime:
        """
        Enhanced regime detection using L2 order book data

        Args:
            orderbook: Optional order book data (uses current if None)

        Returns:
            Detected market regime
        """
        # Use current market metrics if no orderbook provided
        if orderbook is None and self.current_market_metrics:
            metrics = self.current_market_metrics
        elif orderbook:
            # Analyze provided orderbook
            try:
                analysis = self.l2_client.analyze_market_depth(orderbook, depth_levels=5)
                metrics = L2MarketMetrics(
                    spread_bps=analysis.spread_bps,
                    bid_depth=analysis.bid_depth,
                    ask_depth=analysis.ask_depth,
                    imbalance_ratio=analysis.imbalance_ratio,
                    concentration_score=analysis.concentration_score,
                    slippage_estimate_buy=0.0,
                    slippage_estimate_sell=0.0,
                    liquidity_score=self._calculate_liquidity_score(orderbook),
                    volatility_indicator=self._calculate_volatility_indicator(orderbook)
                )
            except Exception:
                return TwapRegime.CALM  # Default fallback
        else:
            return TwapRegime.CALM  # Default fallback

        # Regime detection logic based on L2 metrics
        if metrics.spread_bps > 100:  # >1% spread
            return TwapRegime.VOLATILE
        elif metrics.liquidity_score < 0.5:  # Low liquidity
            return TwapRegime.TOXIC
        elif metrics.volatility_indicator > 0.7:  # High volatility
            return TwapRegime.VOLATILE
        elif abs(metrics.imbalance_ratio) > 0.3:  # Significant imbalance
            return TwapRegime.VOLATILE
        else:
            return TwapRegime.CALM

    async def calculate_optimal_slice_size_with_l2(
        self,
        execution_id: str,
        base_slice_size: Decimal,
        orderbook: Optional[L2OrderBook] = None
    ) -> Decimal:
        """
        Calculate optimal slice size using L2 order book analysis

        Args:
            execution_id: TWAP execution identifier
            base_slice_size: Base slice size from TWAP logic
            orderbook: Optional order book data

        Returns:
            Optimized slice size
        """
        if execution_id not in self.l2_configs:
            return base_slice_size

        config = self.l2_configs[execution_id]

        # Get order book if not provided
        if orderbook is None:
            orderbook = await self.l2_client.get_l2_orderbook(
                config.market_name,
                depth=20
            )

        if not orderbook:
            return base_slice_size

        # Calculate available liquidity
        available_liquidity = self._get_available_liquidity(orderbook, is_buy=True)

        # Apply adaptive sizing logic
        if config.adaptive_sizing:
            # Don't exceed available liquidity
            max_slice_by_liquidity = available_liquidity * Decimal('0.5')  # Use max 50% of available

            # Don't exceed slippage limits
            max_slice_by_slippage = self._calculate_max_slice_by_slippage(orderbook, config)

            # Take the minimum of all constraints
            optimal_size = min(base_slice_size, max_slice_by_liquidity, max_slice_by_slippage)

            # Apply minimum size constraint
            optimal_size = max(optimal_size, Decimal('1000'))  # Minimum 1000 base units

            logger.debug(f"L2 adaptive sizing: base={base_slice_size}, optimal={optimal_size}")
            return optimal_size

        return base_slice_size

    def _get_available_liquidity(self, orderbook: L2OrderBook, is_buy: bool) -> Decimal:
        """Get available liquidity for buy/sell orders"""
        levels = orderbook.bids if is_buy else orderbook.asks
        return sum(level.size for level in levels[:5])  # Top 5 levels

    def _calculate_max_slice_by_slippage(
        self,
        orderbook: L2OrderBook,
        config: L2TwapExecutionConfig
    ) -> Decimal:
        """Calculate maximum slice size that stays within slippage limits"""
        # Test different order sizes to find maximum that stays within slippage limit
        test_sizes = [
            Decimal('100000'),   # 100K
            Decimal('500000'),   # 500K
            Decimal('1000000'),  # 1M
            Decimal('2000000'),  # 2M
            Decimal('5000000'),  # 5M
            Decimal('10000000'), # 10M
        ]

        for size in reversed(test_sizes):  # Start with largest
            slippage = self.l2_client.estimate_slippage(
                orderbook, size, is_buy=True, max_slippage_bps=config.max_slippage_bps
            )

            if abs(slippage['slippage_bps']) <= config.max_slippage_bps:
                return size

        return Decimal('100000')  # Minimum fallback

    async def execute_twap_slice_with_l2(
        self,
        execution_id: str,
        market_index: int,
        base_slice_size: Decimal,
        override_slice_size: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Execute TWAP slice with L2 analysis and optimization

        Args:
            execution_id: TWAP execution identifier
            market_index: Market to place order in
            base_slice_size: Base slice size from TWAP logic
            override_slice_size: Override calculated slice size

        Returns:
            Execution result with L2 analysis
        """
        # Get L2-optimized slice size
        if override_slice_size:
            slice_size = override_slice_size
        else:
            slice_size = await self.calculate_optimal_slice_size_with_l2(
                execution_id, base_slice_size
            )

        # Execute the slice
        result = await self.execute_twap_slice(execution_id, market_index, slice_size)

        # Add L2 analysis to result
        l2_analysis = {}
        if self.current_market_metrics:
            l2_analysis = {
                'market_metrics': {
                    'spread_bps': self.current_market_metrics.spread_bps,
                    'liquidity_score': self.current_market_metrics.liquidity_score,
                    'volatility_indicator': self.current_market_metrics.volatility_indicator,
                    'slice_size_optimization': float(slice_size / base_slice_size)
                }
            }

        return {
            'execution_result': result,
            'l2_analysis': l2_analysis,
            'slice_size_used': slice_size,
            'base_slice_size': base_slice_size
        }

    async def get_l2_enhanced_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get enhanced execution status with L2 market analysis

        Args:
            execution_id: TWAP execution identifier

        Returns:
            Enhanced status with L2 analysis
        """
        # Get base status
        base_status = self.get_twap_status(execution_id)
        if not base_status:
            return None

        # Add L2 analysis
        l2_enhanced = dict(base_status)

        if self.current_market_metrics:
            l2_enhanced['l2_market_analysis'] = {
                'spread_bps': self.current_market_metrics.spread_bps,
                'liquidity_score': self.current_market_metrics.liquidity_score,
                'volatility_indicator': self.current_market_metrics.volatility_indicator,
                'bid_depth': float(self.current_market_metrics.bid_depth),
                'ask_depth': float(self.current_market_metrics.ask_depth),
                'imbalance_ratio': self.current_market_metrics.imbalance_ratio,
                'concentration_score': self.current_market_metrics.concentration_score
            }

        # Add L2 configuration if available
        if execution_id in self.l2_configs:
            config = self.l2_configs[execution_id]
            l2_enhanced['l2_config'] = {
                'market_name': config.market_name,
                'l2_depth_levels': config.l2_depth_levels,
                'max_slippage_bps': config.max_slippage_bps,
                'adaptive_sizing': config.adaptive_sizing,
                'regime_detection_enabled': config.regime_detection_enabled
            }

        return l2_enhanced

    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_market_monitoring()
        await super().cleanup()

# Convenience functions
async def create_l2_twap_execution(
    drift_client,
    swift_client=None,
    market_name: str = "",
    **kwargs
) -> L2AwareTwapExecution:
    """
    Create L2-aware TWAP execution engine

    Args:
        drift_client: Drift client
        swift_client: Optional Swift client
        market_name: Market to monitor
        **kwargs: Additional configuration

    Returns:
        Configured L2-aware TWAP execution engine
    """
    return L2AwareTwapExecution(
        drift_client=drift_client,
        swift_client=swift_client,
        market_name=market_name,
        **kwargs
    )

# Example usage
if __name__ == "__main__":
    async def demo_l2_twap():
        """Demonstrate L2-aware TWAP execution"""

        # Create mock clients (in real usage, these would be actual clients)
        class MockClient:
            pass

        drift_client = MockClient()
        swift_client = MockClient()

        # Create L2-aware TWAP execution
        twap_engine = L2AwareTwapExecution(
            drift_client=drift_client,
            swift_client=swift_client,
            market_name="SOL-PERP"
        )

        print("🔧 L2-Aware TWAP Execution Demo")
        print("=" * 50)

        try:
            # Start market monitoring
            await twap_engine.start_market_monitoring()
            print("✅ Started market monitoring")

            # Wait a bit for market data
            await asyncio.sleep(2)

            # Get market metrics
            if twap_engine.current_market_metrics:
                metrics = twap_engine.current_market_metrics
                print("
📊 Current Market Metrics:"                print(f"   Spread: {metrics.spread_bps:.1f} bps")
                print(f"   Liquidity Score: {metrics.liquidity_score:.2f}")
                print(f"   Volatility Indicator: {metrics.volatility_indicator:.2f}")
                print(f"   Bid Depth: {metrics.bid_depth}")
                print(f"   Ask Depth: {metrics.ask_depth}")

            # Detect regime
            regime = twap_engine.detect_regime_with_l2()
            print(f"\n🎯 Detected Regime: {regime.value}")

            # Simulate TWAP execution
            execution_id = "demo_twap"
            config = L2TwapExecutionConfig(
                market_name="SOL-PERP",
                base_twap_config={}
            )

            print("
🚀 Starting L2-aware TWAP execution..."            success = await twap_engine.start_l2_twap_execution(
                execution_id=execution_id,
                current_position=Decimal('0'),
                target_position=Decimal('1000000'),
                duration_sec=300,
                market_name="SOL-PERP",
                l2_config=config
            )

            if success:
                print("✅ TWAP execution started successfully")

                # Get enhanced status
                status = await twap_engine.get_l2_enhanced_execution_status(execution_id)
                if status:
                    print(f"📈 Execution Progress: {status.get('progress_percentage', 0):.1f}%")

            await asyncio.sleep(5)

        except Exception as e:
            print(f"❌ Demo error: {e}")

        finally:
            await twap_engine.cleanup()
            print("\n🏁 Demo completed")

    asyncio.run(demo_l2_twap())


