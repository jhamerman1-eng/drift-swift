"""
L2 Order Book Engine - Drift Protocol Integration

Advanced L2 order book management system that integrates with Drift Protocol's
comprehensive order book APIs. Provides real-time market microstructure analysis,
liquidity assessment, and intelligent order routing decisions.

Key Features:
- Real-time L2 order book data from Drift DLOB server
- Multi-source liquidity aggregation (vamm, dlob, serum, phoenix, openbook)
- Market microstructure analysis and regime detection
- Slippage estimation and market impact analysis
- Dynamic quote adjustment based on L2 depth
- Integration with ExecutionRouter for intelligent routing

API Integration:
- REST API: https://dlob.drift.trade/l2
- Parameters: marketName, depth, includeOracle, includeVamm
- Response: Comprehensive L2 data with bids/asks, oracle prices, market data

Example API Response Structure:
{
    "bids": [{"price": "1813600", "size": "12000000000", "maker": "...", "orderId": 133325}],
    "asks": [{"price": "1990000", "size": "500000000000", "maker": "...", "orderId": 349}],
    "marketName": "JTO-PERP",
    "marketType": "perp",
    "marketIndex": 20,
    "oracle": 1814244,
    "oracleData": {
        "price": "1814244",
        "slot": "367362076",
        "confidence": "528",
        "twap": "1814244",
        "twapConfidence": "1814244"
    }
}
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
import time
from datetime import datetime

from ..drift.drift_market_adapter import MarketRegime

logger = logging.getLogger(__name__)

@dataclass
class L2Level:
    """L2 order book price level with liquidity source attribution"""
    price: Decimal
    size: Decimal
    maker: Optional[str] = None
    order_id: Optional[int] = None
    sources: Dict[str, Decimal] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'L2Level':
        """Create L2Level from Drift API response"""
        return cls(
            price=Decimal(data['price']),
            size=Decimal(data['size']),
            maker=data.get('maker'),
            order_id=data.get('orderId'),
            sources={'dlob': Decimal(data['size'])}  # Default to dlob source
        )

@dataclass
class L2OrderBook:
    """Complete L2 order book with market data"""
    bids: List[L2Level]
    asks: List[L2Level]
    market_name: str
    market_type: str
    market_index: int
    timestamp: float
    slot: Optional[int] = None
    oracle_price: Optional[Decimal] = None
    oracle_data: Optional[Dict[str, Any]] = None

    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread"""
        if not self.bids or not self.asks:
            return None
        return self.asks[0].price - self.bids[0].price

    @property
    def spread_bps(self) -> Optional[Decimal]:
        """Calculate spread in basis points"""
        if not self.spread or not self.oracle_price:
            return None
        return (self.spread / self.oracle_price) * Decimal('10000')

    @property
    def mid_price(self) -> Optional[Decimal]:
        """Calculate mid price"""
        if not self.bids or not self.asks:
            return None
        return (self.bids[0].price + self.asks[0].price) / Decimal('2')

    def get_depth_at_price(self, price: Decimal, side: str, levels: int = 5) -> Decimal:
        """Get cumulative depth at or better than specified price"""
        if side.lower() == 'bid':
            relevant_levels = [level for level in self.bids[:levels] if level.price >= price]
        else:
            relevant_levels = [level for level in self.asks[:levels] if level.price <= price]

        return sum(level.size for level in relevant_levels)

    def get_volume_profile(self, levels: int = 10) -> Dict[str, Any]:
        """Generate volume profile analysis"""
        bid_sizes = [level.size for level in self.bids[:levels]]
        ask_sizes = [level.size for level in self.asks[:levels]]

        return {
            'bid_volume': sum(bid_sizes),
            'ask_volume': sum(ask_sizes),
            'total_volume': sum(bid_sizes) + sum(ask_sizes),
            'bid_levels': len([s for s in bid_sizes if s > 0]),
            'ask_levels': len([s for s in ask_sizes if s > 0]),
            'volume_imbalance': (sum(bid_sizes) - sum(ask_sizes)) / max(sum(bid_sizes) + sum(ask_sizes), 1)
        }

@dataclass
class MarketMicrostructureMetrics:
    """Comprehensive market microstructure analysis"""
    spread_bps: Optional[Decimal] = None
    depth_imbalance: Decimal = Decimal('0')
    volume_profile: Dict[str, Any] = field(default_factory=dict)
    liquidity_concentration: Decimal = Decimal('0')
    order_book_pressure: Decimal = Decimal('0')
    volatility_regime: str = "normal"
    market_resilience: str = "normal"

class L2OrderBookEngine:
    """
    Advanced L2 Order Book Engine with Drift Protocol Integration

    Provides comprehensive market microstructure analysis and intelligent
    trading decisions based on real-time L2 order book data.
    """

    def __init__(
        self,
        base_url: str = "https://dlob.drift.trade",
        default_depth: int = 20,
        cache_ttl_seconds: float = 1.0,  # 1 second cache
        session_timeout: float = 5.0
    ):
        self.base_url = base_url
        self.default_depth = default_depth
        self.cache_ttl_seconds = cache_ttl_seconds
        self.session_timeout = session_timeout

        # Cache management
        self._cache: Dict[str, Tuple[L2OrderBook, float]] = {}
        self._session: Optional[aiohttp.ClientSession] = None

        # Market analysis thresholds
        self.spread_thresholds = {
            'tight': Decimal('0.001'),      # 0.1% spread = tight
            'normal': Decimal('0.005'),     # 0.5% spread = normal
            'wide': Decimal('0.01')         # 1.0% spread = wide
        }

        self.depth_thresholds = {
            'low': Decimal('10'),           # Low liquidity
            'normal': Decimal('50'),        # Normal liquidity
            'high': Decimal('100')          # High liquidity
        }

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def initialize(self):
        """Initialize HTTP session"""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.session_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("L2OrderBookEngine initialized")

    async def close(self):
        """Close HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("L2OrderBookEngine closed")

    async def get_l2_orderbook(
        self,
        market_name: str,
        depth: Optional[int] = None,
        include_oracle: bool = True,
        include_vamm: bool = True,
        use_cache: bool = True
    ) -> Optional[L2OrderBook]:
        """
        Fetch L2 order book from Drift DLOB server

        Args:
            market_name: Market identifier (e.g., "JTO-PERP")
            depth: Number of price levels to fetch
            include_oracle: Include oracle price data
            include_vamm: Include VAMM liquidity
            use_cache: Use cached data if available

        Returns:
            L2OrderBook instance or None if failed
        """
        if self._session is None:
            await self.initialize()

        cache_key = f"{market_name}_{depth}_{include_oracle}_{include_vamm}"

        # Check cache
        if use_cache and cache_key in self._cache:
            cached_data, cache_time = self._cache[cache_key]
            if time.time() - cache_time < self.cache_ttl_seconds:
                return cached_data

        # Build API URL
        url = f"{self.base_url}/l2"
        params = {
            'marketName': market_name,
            'depth': depth or self.default_depth,
            'includeOracle': str(include_oracle).lower(),
            'includeVamm': str(include_vamm).lower()
        }

        try:
            async with self._session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"L2 API request failed: {response.status}")
                    return None

                data = await response.json()
                orderbook = self._parse_api_response(data)

                # Cache result
                if use_cache:
                    self._cache[cache_key] = (orderbook, time.time())

                return orderbook

        except Exception as e:
            logger.error(f"Failed to fetch L2 orderbook for {market_name}: {e}")
            return None

    def _parse_api_response(self, data: Dict[str, Any]) -> L2OrderBook:
        """Parse Drift API response into L2OrderBook"""
        bids = [L2Level.from_api_response(bid) for bid in data.get('bids', [])]
        asks = [L2Level.from_api_response(ask) for ask in data.get('asks', [])]

        # Sort bids descending (highest price first), asks ascending (lowest price first)
        bids.sort(key=lambda x: x.price, reverse=True)
        asks.sort(key=lambda x: x.price)

        oracle_price = None
        if 'oracle' in data:
            oracle_price = Decimal(str(data['oracle']))

        return L2OrderBook(
            bids=bids,
            asks=asks,
            market_name=data.get('marketName', ''),
            market_type=data.get('marketType', ''),
            market_index=data.get('marketIndex', 0),
            timestamp=time.time(),
            slot=data.get('slot'),
            oracle_price=oracle_price,
            oracle_data=data.get('oracleData')
        )

    def analyze_market_microstructure(
        self,
        orderbook: L2OrderBook,
        analysis_depth: int = 10
    ) -> MarketMicrostructureMetrics:
        """
        Perform comprehensive market microstructure analysis

        Args:
            orderbook: L2 order book to analyze
            analysis_depth: Number of price levels to analyze

        Returns:
            MarketMicrostructureMetrics with detailed analysis
        """
        metrics = MarketMicrostructureMetrics()

        # Spread analysis
        metrics.spread_bps = orderbook.spread_bps

        # Volume profile analysis
        metrics.volume_profile = orderbook.get_volume_profile(analysis_depth)

        # Depth imbalance calculation
        bid_volume = metrics.volume_profile['bid_volume']
        ask_volume = metrics.volume_profile['ask_volume']
        total_volume = bid_volume + ask_volume

        if total_volume > 0:
            metrics.depth_imbalance = (bid_volume - ask_volume) / total_volume

        # Order book pressure (simplified)
        if len(orderbook.bids) >= 3 and len(orderbook.asks) >= 3:
            bid_pressure = sum(level.size for level in orderbook.bids[:3])
            ask_pressure = sum(level.size for level in orderbook.asks[:3])
            metrics.order_book_pressure = (bid_pressure - ask_pressure) / max(bid_pressure + ask_pressure, 1)

        # Volatility regime detection
        if metrics.spread_bps:
            if metrics.spread_bps < self.spread_thresholds['tight']:
                metrics.volatility_regime = "low"
            elif metrics.spread_bps > self.spread_thresholds['wide']:
                metrics.volatility_regime = "high"
            else:
                metrics.volatility_regime = "normal"

        # Market resilience assessment
        total_levels = len(orderbook.bids) + len(orderbook.asks)
        if total_levels < 10:
            metrics.market_resilience = "low"
        elif total_levels > 30:
            metrics.market_resilience = "high"
        else:
            metrics.market_resilience = "normal"

        return metrics

    def estimate_slippage(
        self,
        orderbook: L2OrderBook,
        order_size: Decimal,
        side: str,
        max_slippage_bps: Decimal = Decimal('50')  # 0.5%
    ) -> Dict[str, Any]:
        """
        Estimate slippage for a given order size

        Args:
            orderbook: L2 order book
            order_size: Size of order to estimate slippage for
            side: 'bid' or 'ask'
            max_slippage_bps: Maximum acceptable slippage in basis points

        Returns:
            Slippage estimation results
        """
        if side.lower() == 'bid':
            levels = orderbook.asks  # Buying from asks
            reference_price = orderbook.bids[0].price if orderbook.bids else None
        else:
            levels = orderbook.bids  # Selling to bids
            reference_price = orderbook.asks[0].price if orderbook.asks else None

        if not reference_price or not levels:
            return {
                'slippage_bps': None,
                'execution_price': None,
                'feasible': False,
                'reason': 'Insufficient liquidity'
            }

        # Simulate order execution
        remaining_size = order_size
        total_cost = Decimal('0')
        weighted_price = Decimal('0')

        for level in levels:
            if remaining_size <= 0:
                break

            fill_size = min(remaining_size, level.size)
            remaining_size -= fill_size
            total_cost += fill_size * level.price

        if remaining_size > 0:
            return {
                'slippage_bps': None,
                'execution_price': None,
                'feasible': False,
                'reason': 'Insufficient depth'
            }

        if order_size > 0:
            execution_price = total_cost / order_size
            slippage = execution_price - reference_price
            slippage_bps = (slippage / reference_price) * Decimal('10000')

            return {
                'slippage_bps': float(slippage_bps),
                'execution_price': float(execution_price),
                'feasible': abs(slippage_bps) <= max_slippage_bps,
                'reference_price': float(reference_price),
                'slippage_amount': float(slippage)
            }

        return {
            'slippage_bps': 0,
            'execution_price': float(reference_price),
            'feasible': True,
            'reference_price': float(reference_price),
            'slippage_amount': 0
        }

    def detect_market_regime(self, orderbook: L2OrderBook) -> MarketRegime:
        """
        Detect market regime from L2 order book characteristics

        Args:
            orderbook: L2 order book to analyze

        Returns:
            Detected market regime
        """
        if not orderbook.spread_bps:
            return MarketRegime.CALM

        # Analyze spread
        spread_too_wide = orderbook.spread_bps > self.spread_thresholds['wide']

        # Analyze depth
        top_bid_depth = sum(level.size for level in orderbook.bids[:5])
        top_ask_depth = sum(level.size for level in orderbook.asks[:5])
        avg_depth = (top_bid_depth + top_ask_depth) / 2
        depth_too_low = avg_depth < self.depth_thresholds['low']

        # Regime classification
        if spread_too_wide and depth_too_low:
            return MarketRegime.TOXIC
        elif spread_too_wide or depth_too_low:
            return MarketRegime.VOLATILE
        else:
            return MarketRegime.CALM

    def calculate_optimal_slice_size(
        self,
        orderbook: L2OrderBook,
        target_position: Decimal,
        side: str,
        max_market_impact_bps: Decimal = Decimal('10')  # 0.1%
    ) -> Dict[str, Any]:
        """
        Calculate optimal slice size based on L2 liquidity

        Args:
            orderbook: L2 order book
            target_position: Total position size to achieve
            side: 'bid' or 'ask'
            max_market_impact_bps: Maximum acceptable market impact

        Returns:
            Optimal slice size recommendations
        """
        # Get available liquidity at top levels
        top_levels = 3
        if side.lower() == 'bid':
            available_liquidity = sum(level.size for level in orderbook.asks[:top_levels])
        else:
            available_liquidity = sum(level.size for level in orderbook.bids[:top_levels])

        # Conservative slice size (don't consume more than 30% of top liquidity)
        conservative_slice = available_liquidity * Decimal('0.3')

        # Target-based slice (10% of target position)
        target_based_slice = target_position * Decimal('0.1')

        # Market impact constrained slice
        if orderbook.spread and orderbook.oracle_price:
            # Estimate price impact for different slice sizes
            test_sizes = [
                target_based_slice * Decimal('0.5'),
                target_based_slice,
                target_based_slice * Decimal('2')
            ]

            for test_size in test_sizes:
                slippage_analysis = self.estimate_slippage(
                    orderbook, test_size, side, max_market_impact_bps
                )

                if slippage_analysis['feasible']:
                    impact_constrained_slice = test_size
                    break
            else:
                # If no feasible size found, use conservative approach
                impact_constrained_slice = conservative_slice
        else:
            impact_constrained_slice = conservative_slice

        # Final recommendation (minimum of all constraints)
        optimal_slice = min(conservative_slice, target_based_slice, impact_constrained_slice)

        return {
            'optimal_slice_size': optimal_slice,
            'conservative_slice': conservative_slice,
            'target_based_slice': target_based_slice,
            'impact_constrained_slice': impact_constrained_slice,
            'available_liquidity': available_liquidity,
            'liquidity_utilization_rate': float(optimal_slice / available_liquidity) if available_liquidity > 0 else 0
        }

# Convenience functions for external use
async def get_drift_l2_orderbook(
    market_name: str,
    depth: int = 20,
    include_oracle: bool = True,
    include_vamm: bool = True
) -> Optional[L2OrderBook]:
    """Convenience function to fetch Drift L2 order book"""
    async with L2OrderBookEngine() as engine:
        return await engine.get_l2_orderbook(
            market_name=market_name,
            depth=depth,
            include_oracle=include_oracle,
            include_vamm=include_vamm
        )

def analyze_market_regime(orderbook: L2OrderBook) -> Dict[str, Any]:
    """Convenience function for market regime analysis"""
    engine = L2OrderBookEngine()
    metrics = engine.analyze_market_microstructure(orderbook)

    return {
        'regime': engine.detect_market_regime(orderbook).value,
        'spread_bps': float(metrics.spread_bps) if metrics.spread_bps else None,
        'depth_imbalance': float(metrics.depth_imbalance),
        'volatility_regime': metrics.volatility_regime,
        'market_resilience': metrics.market_resilience,
        'volume_profile': metrics.volume_profile
    }

def estimate_order_slippage(
    orderbook: L2OrderBook,
    order_size: Decimal,
    side: str
) -> Dict[str, Any]:
    """Convenience function for slippage estimation"""
    engine = L2OrderBookEngine()
    return engine.estimate_slippage(orderbook, order_size, side)
