"""
Drift Protocol L2 Order Book Client

Official integration with Drift's DLOB (Decentralized Limit Order Book) server
for real-time L2 and L3 order book data. Provides market depth analysis,
liquidity monitoring, and trading decision support.

Based on: https://drift-labs.github.io/v2-teacher/#get-l2-l3
API Endpoint: https://dlob.drift.trade/l2

Key Features:
- Real-time L2 order book data
- Oracle price integration
- VAMM (Virtual AMM) liquidity
- Market depth analysis
- Slippage estimation
- Liquidity risk assessment
"""

import asyncio
import httpx
import json
import time
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime

from ..configs.centralized_config_manager import config_manager

logger = logging.getLogger(__name__)

@dataclass
class L2OrderBookLevel:
    """Represents a single level in the L2 order book"""
    price: Decimal
    size: Decimal
    maker: Optional[str] = None
    order_id: Optional[int] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'L2OrderBookLevel':
        """Create L2OrderBookLevel from API response data"""
        return cls(
            price=Decimal(str(data['price'])),
            size=Decimal(str(data['size'])),
            maker=data.get('maker'),
            order_id=data.get('orderId')
        )

@dataclass
class L3OrderBookLevel:
    """Represents a single level in the L3 order book (individual orders)"""
    price: Decimal
    size: Decimal
    maker: str
    order_id: int

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'L3OrderBookLevel':
        """Create L3OrderBookLevel from API response data"""
        return cls(
            price=Decimal(str(data['price'])),
            size=Decimal(str(data['size'])),
            maker=data['maker'],
            order_id=data['orderId']
        )

@dataclass
class OracleData:
    """Oracle price data from the order book response"""
    price: Decimal
    slot: int
    confidence: Optional[Decimal] = None
    has_sufficient_data_points: bool = True
    twap: Optional[Decimal] = None
    twap_confidence: Optional[Decimal] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'OracleData':
        """Create OracleData from API response"""
        return cls(
            price=Decimal(str(data['price'])),
            slot=int(data['slot']),
            confidence=Decimal(str(data['confidence'])) if 'confidence' in data else None,
            has_sufficient_data_points=data.get('hasSufficientNumberOfDataPoints', True),
            twap=Decimal(str(data['twap'])) if 'twap' in data else None,
            twap_confidence=Decimal(str(data['twapConfidence'])) if 'twapConfidence' in data else None
        )

@dataclass
class L2OrderBook:
    """Complete L2 order book data structure"""
    bids: List[L2OrderBookLevel] = field(default_factory=list)
    asks: List[L2OrderBookLevel] = field(default_factory=list)
    market_name: str = ""
    market_type: str = ""
    market_index: int = 0
    slot: Optional[int] = None
    timestamp: Optional[int] = None
    oracle_price: Optional[OracleData] = None
    mm_oracle_price: Optional[OracleData] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'L2OrderBook':
        """Create L2OrderBook from API response data"""
        return cls(
            bids=[L2OrderBookLevel.from_api_response(bid) for bid in data.get('bids', [])],
            asks=[L2OrderBookLevel.from_api_response(ask) for ask in data.get('asks', [])],
            market_name=data.get('marketName', ''),
            market_type=data.get('marketType', ''),
            market_index=data.get('marketIndex', 0),
            slot=data.get('slot'),
            timestamp=data.get('ts'),
            oracle_price=OracleData.from_api_response(data['oracleData']) if 'oracleData' in data else None,
            mm_oracle_price=OracleData.from_api_response(data['mmOracleData']) if 'mmOracleData' in data else None
        )

@dataclass
class L3OrderBook:
    """Complete L3 order book data structure"""
    bids: List[L3OrderBookLevel] = field(default_factory=list)
    asks: List[L3OrderBookLevel] = field(default_factory=list)
    slot: Optional[int] = None

@dataclass
class MarketDepthAnalysis:
    """Analysis of market depth and liquidity"""
    spread_bps: float
    bid_depth: Decimal
    ask_depth: Decimal
    total_depth: Decimal
    bid_levels: int
    ask_levels: int
    imbalance_ratio: float
    concentration_score: float

class DriftL2OrderBookClient:
    """
    Official Drift Protocol L2 Order Book Client

    Provides real-time access to Drift's DLOB (Decentralized Limit Order Book)
    with market analysis capabilities for enhanced trading decisions.

    API Reference: https://drift-labs.github.io/v2-teacher/#get-l2-l3
    """

    def __init__(
        self,
        base_url: str = "https://dlob.drift.trade",
        timeout_seconds: float = 5.0,
        max_retries: int = 3
    ):
        """
        Initialize the L2 order book client

        Args:
            base_url: Base URL for the DLOB API
            timeout_seconds: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

        # HTTP client for API requests
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={'User-Agent': 'Drift-Swift-Trading-Bot'}
        )

        # Cache for order book data
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 1.0  # 1 second cache TTL

        logger.info(f"Initialized Drift L2 Order Book Client: {base_url}")

    async def get_l2_orderbook(
        self,
        market_name: str,
        depth: int = 10,
        include_oracle: bool = True,
        include_vamm: bool = True,
        use_cache: bool = True
    ) -> Optional[L2OrderBook]:
        """
        Get L2 order book for a specific market

        Args:
            market_name: Market name (e.g., 'SOL-PERP', 'BTC-PERP')
            depth: Number of price levels to retrieve
            include_oracle: Include oracle price data
            include_vamm: Include VAMM liquidity
            use_cache: Use cached data if available

        Returns:
            L2OrderBook instance or None if request failed
        """
        cache_key = f"l2_{market_name}_{depth}_{include_oracle}_{include_vamm}"

        # Check cache first
        if use_cache and self._is_cache_valid(cache_key):
            cached_data = self._cache[cache_key]
            return L2OrderBook.from_api_response(cached_data)

        # Build API request parameters
        params = {
            'marketName': market_name,
            'depth': str(depth)
        }

        if include_oracle:
            params['includeOracle'] = 'true'
        if include_vamm:
            params['includeVamm'] = 'true'

        # Make API request
        try:
            response = await self.client.get('/l2', params=params)

            if response.status_code != 200:
                logger.error(f"L2 API request failed: {response.status_code} - {response.text}")
                return None

            data = response.json()

            # Cache the response
            self._cache[cache_key] = data
            self._cache[cache_key + '_timestamp'] = time.time()

            # Parse and return order book
            orderbook = L2OrderBook.from_api_response(data)
            logger.debug(f"Retrieved L2 order book for {market_name}: {len(orderbook.bids)} bids, {len(orderbook.asks)} asks")

            return orderbook

        except Exception as e:
            logger.error(f"Failed to retrieve L2 order book for {market_name}: {e}")
            return None

    async def get_l3_orderbook(
        self,
        market_name: str,
        depth: int = 10,
        use_cache: bool = True
    ) -> Optional[L3OrderBook]:
        """
        Get L3 order book (individual orders) for a specific market

        Args:
            market_name: Market name (e.g., 'SOL-PERP', 'BTC-PERP')
            depth: Number of price levels to retrieve
            use_cache: Use cached data if available

        Returns:
            L3OrderBook instance or None if request failed
        """
        cache_key = f"l3_{market_name}_{depth}"

        # Check cache first
        if use_cache and self._is_cache_valid(cache_key):
            cached_data = self._cache[cache_key]
            return self._parse_l3_response(cached_data)

        # Make API request
        try:
            params = {
                'marketName': market_name,
                'depth': str(depth)
            }

            response = await self.client.get('/l3', params=params)

            if response.status_code != 200:
                logger.error(f"L3 API request failed: {response.status_code} - {response.text}")
                return None

            data = response.json()

            # Cache the response
            self._cache[cache_key] = data
            self._cache[cache_key + '_timestamp'] = time.time()

            # Parse and return order book
            orderbook = self._parse_l3_response(data)
            logger.debug(f"Retrieved L3 order book for {market_name}: {len(orderbook.bids)} bids, {len(orderbook.asks)} asks")

            return orderbook

        except Exception as e:
            logger.error(f"Failed to retrieve L3 order book for {market_name}: {e}")
            return None

    def _parse_l3_response(self, data: Dict[str, Any]) -> L3OrderBook:
        """Parse L3 API response into L3OrderBook structure"""
        return L3OrderBook(
            bids=[L3OrderBookLevel.from_api_response(bid) for bid in data.get('bids', [])],
            asks=[L3OrderBookLevel.from_api_response(ask) for ask in data.get('asks', [])],
            slot=data.get('slot')
        )

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        cache_timestamp_key = cache_key + '_timestamp'
        if cache_timestamp_key not in self._cache:
            return False

        cache_age = time.time() - self._cache[cache_timestamp_key]
        return cache_age < self._cache_ttl

    def analyze_market_depth(self, orderbook: L2OrderBook, depth_levels: int = 5) -> MarketDepthAnalysis:
        """
        Analyze market depth and liquidity characteristics

        Args:
            orderbook: L2 order book to analyze
            depth_levels: Number of price levels to include in depth calculation

        Returns:
            MarketDepthAnalysis with comprehensive market depth metrics
        """
        if not orderbook.bids or not orderbook.asks:
            raise ValueError("Order book must have both bids and asks for analysis")

        # Calculate spread
        best_bid = orderbook.bids[0].price
        best_ask = orderbook.asks[0].price
        mid_price = (best_bid + best_ask) / 2
        spread_bps = float(((best_ask - best_bid) / mid_price) * 10000)

        # Calculate depth
        bid_depth = sum(level.size for level in orderbook.bids[:depth_levels])
        ask_depth = sum(level.size for level in orderbook.asks[:depth_levels])
        total_depth = bid_depth + ask_depth

        # Calculate imbalance
        imbalance_ratio = float((bid_depth - ask_depth) / total_depth) if total_depth > 0 else 0.0

        # Calculate concentration (how much liquidity is in top levels)
        total_bid_liquidity = sum(level.size for level in orderbook.bids)
        total_ask_liquidity = sum(level.size for level in orderbook.asks)

        top_bid_percentage = float((bid_depth / total_bid_liquidity) * 100) if total_bid_liquidity > 0 else 0.0
        top_ask_percentage = float((ask_depth / total_ask_liquidity) * 100) if total_ask_liquidity > 0 else 0.0
        concentration_score = (top_bid_percentage + top_ask_percentage) / 2

        return MarketDepthAnalysis(
            spread_bps=spread_bps,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            total_depth=total_depth,
            bid_levels=min(depth_levels, len(orderbook.bids)),
            ask_levels=min(depth_levels, len(orderbook.asks)),
            imbalance_ratio=imbalance_ratio,
            concentration_score=concentration_score
        )

    def estimate_slippage(
        self,
        orderbook: L2OrderBook,
        order_size: Decimal,
        is_buy: bool = True,
        max_slippage_bps: float = 500.0
    ) -> Dict[str, Any]:
        """
        Estimate slippage for a given order size

        Args:
            orderbook: L2 order book data
            order_size: Size of the order to estimate slippage for
            is_buy: True for buy order, False for sell order
            max_slippage_bps: Maximum acceptable slippage in basis points

        Returns:
            Dictionary with slippage estimation results
        """
        levels = orderbook.bids if is_buy else orderbook.asks
        remaining_size = order_size

        total_cost = Decimal('0')
        weighted_price = Decimal('0')
        total_executed = Decimal('0')

        for level in levels:
            if remaining_size <= 0:
                break

            execute_size = min(remaining_size, level.size)
            cost = execute_size * level.price

            total_cost += cost
            total_executed += execute_size
            remaining_size -= execute_size

        if total_executed == 0:
            return {
                'slippage_bps': 0.0,
                'execution_price': 0.0,
                'filled_percentage': 0.0,
                'market_impact': 'insufficient_liquidity'
            }

        # Calculate execution price
        execution_price = float(total_cost / total_executed)

        # Get reference price
        reference_price = float(orderbook.asks[0].price if is_buy else orderbook.bids[0].price)

        # Calculate slippage
        slippage_bps = ((execution_price - reference_price) / reference_price) * 10000
        if not is_buy:
            slippage_bps = -slippage_bps  # Negative slippage for sells

        filled_percentage = float((total_executed / order_size) * 100)

        return {
            'slippage_bps': slippage_bps,
            'execution_price': execution_price,
            'reference_price': reference_price,
            'filled_percentage': filled_percentage,
            'market_impact': 'acceptable' if abs(slippage_bps) <= max_slippage_bps else 'high',
            'remaining_size': float(remaining_size)
        }

    async def monitor_market_conditions(
        self,
        market_name: str,
        interval_seconds: float = 1.0,
        callback: Optional[callable] = None
    ) -> None:
        """
        Monitor market conditions in real-time

        Args:
            market_name: Market to monitor
            interval_seconds: Monitoring interval
            callback: Optional callback function for analysis results
        """
        logger.info(f"Starting market condition monitoring for {market_name}")

        while True:
            try:
                # Get current order book
                orderbook = await self.get_l2_orderbook(market_name, depth=20)

                if orderbook:
                    # Analyze market depth
                    analysis = self.analyze_market_depth(orderbook)

                    # Estimate slippage for typical order sizes
                    slippage_buy = self.estimate_slippage(orderbook, Decimal('1000000'), is_buy=True)
                    slippage_sell = self.estimate_slippage(orderbook, Decimal('1000000'), is_buy=False)

                    monitoring_data = {
                        'timestamp': datetime.now().isoformat(),
                        'market': market_name,
                        'analysis': analysis,
                        'slippage_buy': slippage_buy,
                        'slippage_sell': slippage_sell,
                        'oracle_price': float(orderbook.oracle_price.price) if orderbook.oracle_price else None
                    }

                    if callback:
                        await callback(monitoring_data)

                    logger.debug(f"Market monitoring update for {market_name}: spread={analysis.spread_bps:.1f}bps")

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Market monitoring error for {market_name}: {e}")
                await asyncio.sleep(interval_seconds)

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Global client instance
l2_client = DriftL2OrderBookClient()

# Convenience functions for easy access
async def get_l2_orderbook(market_name: str, depth: int = 10) -> Optional[L2OrderBook]:
    """Convenience function to get L2 order book"""
    return await l2_client.get_l2_orderbook(market_name, depth)

async def analyze_market_depth(market_name: str, depth_levels: int = 5) -> Optional[MarketDepthAnalysis]:
    """Convenience function to analyze market depth"""
    orderbook = await get_l2_orderbook(market_name, depth=20)
    if orderbook:
        return l2_client.analyze_market_depth(orderbook, depth_levels)
    return None

# Example usage and testing
if __name__ == "__main__":
    async def main():
        print("🔍 Testing Drift L2 Order Book Client")
        print("=" * 50)

        try:
            # Test L2 order book retrieval
            print("\n📊 Getting L2 Order Book for JTO-PERP...")
            orderbook = await get_l2_orderbook("JTO-PERP", depth=10)

            if orderbook:
                print("✅ Order book retrieved successfully!"                print(f"   Market: {orderbook.market_name}")
                print(f"   Bids: {len(orderbook.bids)} levels")
                print(f"   Asks: {len(orderbook.asks)} levels")
                print(f"   Oracle Price: {orderbook.oracle_price.price if orderbook.oracle_price else 'N/A'}")

                # Test market depth analysis
                print("
📈 Analyzing Market Depth..."                analysis = l2_client.analyze_market_depth(orderbook)
                print(f"   Spread: {analysis.spread_bps:.1f} bps")
                print(f"   Total Depth: {analysis.total_depth}")
                print(f"   Imbalance: {analysis.imbalance_ratio:.2%}")

                # Test slippage estimation
                print("
💰 Estimating Slippage for 1M base units..."                slippage_buy = l2_client.estimate_slippage(orderbook, Decimal('1000000'), is_buy=True)
                slippage_sell = l2_client.estimate_slippage(orderbook, Decimal('1000000'), is_buy=False)

                print(f"   Buy Slippage: {slippage_buy['slippage_bps']:.1f} bps")
                print(f"   Sell Slippage: {slippage_sell['slippage_bps']:.1f} bps")

            else:
                print("❌ Failed to retrieve order book")

        except Exception as e:
            print(f"❌ Error: {e}")

        finally:
            await l2_client.close()

    asyncio.run(main())


