#!/usr/bin/env python3
"""
JIT v3.0 Integration Layer
Adapters for Swift/DriftPy integration with the JIT engine
"""

import asyncio
import logging
from typing import Dict, Any, Tuple, Optional, Union
from abc import ABC, abstractmethod

from .core import TradingClient, MarketData

logger = logging.getLogger(__name__)

class SwiftTradingClient(TradingClient):
    """Trading client adapter for Swift sidecar integration"""
    
    def __init__(self, swift_client, market_index: int = 0):
        self.swift_client = swift_client
        self.market_index = market_index
        self._cached_position = 0.0
        self._position_cache_time = 0.0
        self._position_cache_ttl = 1.0  # 1 second cache
        
    async def get_orderbook(self) -> Dict[str, Any]:
        """Get orderbook from Swift client"""
        try:
            # Adapt Swift client orderbook format to standard format
            orderbook = await self.swift_client.get_orderbook(self.market_index)
            
            # Convert to standard format expected by JIT engine
            return {
                'bids': [(level['price'], level['size']) for level in orderbook.get('bids', [])],
                'asks': [(level['price'], level['size']) for level in orderbook.get('asks', [])],
                'timestamp': orderbook.get('timestamp', 0)
            }
        except Exception as e:
            logger.error(f"Failed to get orderbook from Swift: {e}")
            raise
    
    async def get_position(self) -> float:
        """Get current position from Swift client with caching"""
        try:
            import time
            now = time.time()
            
            # Use cached position if recent
            if now - self._position_cache_time < self._position_cache_ttl:
                return self._cached_position
            
            # Fetch fresh position
            position_data = await self.swift_client.get_position(self.market_index)
            self._cached_position = position_data.get('base_asset_amount', 0.0)
            self._position_cache_time = now
            
            return self._cached_position
            
        except Exception as e:
            logger.warning(f"Failed to get position from Swift: {e}")
            return self._cached_position  # Return cached value on error
    
    async def get_realized_volatility(self) -> float:
        """Get realized volatility from Swift client"""
        try:
            # Swift may not provide volatility directly
            # Use orderbook spread as a proxy
            orderbook = await self.get_orderbook()
            if not orderbook['bids'] or not orderbook['asks']:
                return 0.001  # Default volatility
            
            best_bid = orderbook['bids'][0][0]
            best_ask = orderbook['asks'][0][0]
            mid = (best_bid + best_ask) / 2.0
            spread_pct = (best_ask - best_bid) / mid
            
            return min(0.1, max(0.0001, spread_pct))  # Clamp between 0.01% and 10%
            
        except Exception as e:
            logger.warning(f"Failed to get volatility from Swift: {e}")
            return 0.001
    
    async def place_orders(self, 
                          bid_price: float, 
                          ask_price: float,
                          bid_size: float, 
                          ask_size: float) -> Tuple[str, str]:
        """Place bid and ask orders via Swift client"""
        try:
            # Cancel existing orders first (if needed)
            await self.cancel_all_orders()
            
            # Place new orders
            bid_order_id = await self.swift_client.place_order(
                market_index=self.market_index,
                side='buy',
                price=bid_price,
                size=bid_size,
                order_type='limit',
                post_only=True
            )
            
            ask_order_id = await self.swift_client.place_order(
                market_index=self.market_index,
                side='sell', 
                price=ask_price,
                size=ask_size,
                order_type='limit',
                post_only=True
            )
            
            logger.info(f"Placed orders: bid={bid_order_id} ask={ask_order_id}")
            return bid_order_id, ask_order_id
            
        except Exception as e:
            logger.error(f"Failed to place orders via Swift: {e}")
            raise
    
    async def cancel_all_orders(self) -> None:
        """Cancel all orders via Swift client"""
        try:
            await self.swift_client.cancel_all_orders(self.market_index)
        except Exception as e:
            logger.warning(f"Failed to cancel orders via Swift: {e}")

class DriftPyTradingClient(TradingClient):
    """Trading client adapter for DriftPy integration"""
    
    def __init__(self, drift_client, market_index: int = 0):
        self.drift_client = drift_client
        self.market_index = market_index
        self._cached_position = 0.0
        self._position_cache_time = 0.0
        self._position_cache_ttl = 1.0
    
    async def get_orderbook(self) -> Dict[str, Any]:
        """Get orderbook from DriftPy client"""
        try:
            # Get orderbook from DriftPy
            orderbook = self.drift_client.get_orderbook(self.market_index)
            
            # Convert to standard format
            return {
                'bids': [(float(level.price), float(level.size)) for level in orderbook.bids],
                'asks': [(float(level.price), float(level.size)) for level in orderbook.asks],
                'timestamp': orderbook.timestamp
            }
        except Exception as e:
            logger.error(f"Failed to get orderbook from DriftPy: {e}")
            raise
    
    async def get_position(self) -> float:
        """Get current position from DriftPy client"""
        try:
            import time
            now = time.time()
            
            if now - self._position_cache_time < self._position_cache_ttl:
                return self._cached_position
            
            user = self.drift_client.get_user()
            perp_position = user.get_perp_position(self.market_index)
            self._cached_position = float(perp_position.base_asset_amount) / 1e9  # Convert from native units
            self._position_cache_time = now
            
            return self._cached_position
            
        except Exception as e:
            logger.warning(f"Failed to get position from DriftPy: {e}")
            return self._cached_position
    
    async def get_realized_volatility(self) -> float:
        """Get realized volatility from DriftPy client"""
        try:
            # DriftPy may provide oracle price volatility
            oracle = self.drift_client.get_oracle_price_data(self.market_index)
            if hasattr(oracle, 'volatility'):
                return float(oracle.volatility) / 1e6  # Normalize
            
            # Fallback to spread-based volatility
            orderbook = await self.get_orderbook()
            if not orderbook['bids'] or not orderbook['asks']:
                return 0.001
            
            best_bid = orderbook['bids'][0][0]
            best_ask = orderbook['asks'][0][0]
            mid = (best_bid + best_ask) / 2.0
            spread_pct = (best_ask - best_bid) / mid
            
            return min(0.1, max(0.0001, spread_pct))
            
        except Exception as e:
            logger.warning(f"Failed to get volatility from DriftPy: {e}")
            return 0.001
    
    async def place_orders(self, 
                          bid_price: float,
                          ask_price: float, 
                          bid_size: float,
                          ask_size: float) -> Tuple[str, str]:
        """Place orders via DriftPy client"""
        try:
            from driftpy.types import OrderParams, OrderType, MarketType, PositionDirection, PostOnlyParams
            
            # Cancel existing orders
            await self.cancel_all_orders()
            
            # Place bid order
            bid_params = OrderParams(
                order_type=OrderType.Limit(),
                market_type=MarketType.Perp(),
                direction=PositionDirection.Long(),
                user_order_id=int(time.time() * 1000) % 2**32,  # Simple order ID
                base_asset_amount=int(bid_size * 1e9),  # Convert to native units
                price=int(bid_price * 1e6),  # Convert to price precision
                market_index=self.market_index,
                post_only=PostOnlyParams.MustPostOnly()
            )
            
            ask_params = OrderParams(
                order_type=OrderType.Limit(),
                market_type=MarketType.Perp(),
                direction=PositionDirection.Short(),
                user_order_id=(int(time.time() * 1000) + 1) % 2**32,
                base_asset_amount=int(ask_size * 1e9),
                price=int(ask_price * 1e6),
                market_index=self.market_index,
                post_only=PostOnlyParams.MustPostOnly()
            )
            
            # Submit orders
            bid_tx = await self.drift_client.place_perp_order(bid_params)
            ask_tx = await self.drift_client.place_perp_order(ask_params)
            
            logger.info(f"Placed DriftPy orders: bid={bid_tx} ask={ask_tx}")
            return str(bid_tx), str(ask_tx)
            
        except Exception as e:
            logger.error(f"Failed to place orders via DriftPy: {e}")
            raise
    
    async def cancel_all_orders(self) -> None:
        """Cancel all orders via DriftPy client"""
        try:
            await self.drift_client.cancel_all_orders()
        except Exception as e:
            logger.warning(f"Failed to cancel orders via DriftPy: {e}")

class JITEngineAdapter:
    """
    High-level adapter that integrates JIT engine with existing MM bot infrastructure
    """
    
    def __init__(self, 
                 jit_engine,
                 trading_client: TradingClient,
                 config: Dict[str, Any]):
        self.jit_engine = jit_engine
        self.trading_client = trading_client
        self.config = config
        self._last_quote_time = 0.0
        
    async def tick(self) -> Dict[str, Any]:
        """
        Execute one JIT tick and place orders if needed
        
        Returns:
            Dict with tick results and metrics
        """
        tick_start = time.time()
        
        try:
            # Run JIT engine step
            decision = await self.jit_engine.step()
            
            if decision is None:
                return {
                    'action': 'skip',
                    'reason': 'no_decision',
                    'latency_ms': (time.time() - tick_start) * 1000
                }
            
            if not decision.should_quote:
                return {
                    'action': 'skip', 
                    'reason': decision.reason,
                    'toxicity': decision.toxicity_score,
                    'regime': decision.regime.value,
                    'latency_ms': (time.time() - tick_start) * 1000
                }
            
            # Calculate order prices
            half_spread = decision.spread_bps / 20000.0  # Convert bps to decimal, then half
            bid_price = decision.ref_price * (1.0 - half_spread)
            ask_price = decision.ref_price * (1.0 + half_spread)
            
            # Place orders via trading client
            bid_id, ask_id = await self.trading_client.place_orders(
                bid_price=bid_price,
                ask_price=ask_price,
                bid_size=decision.bid_size,
                ask_size=decision.ask_size
            )
            
            self._last_quote_time = time.time()
            
            return {
                'action': 'quote',
                'bid_id': bid_id,
                'ask_id': ask_id,
                'ref_price': decision.ref_price,
                'spread_bps': decision.spread_bps,
                'bid_price': bid_price,
                'ask_price': ask_price,
                'bid_size': decision.bid_size,
                'ask_size': decision.ask_size,
                'toxicity': decision.toxicity_score,
                'regime': decision.regime.value,
                'reason': decision.reason,
                'latency_ms': (time.time() - tick_start) * 1000
            }
            
        except Exception as e:
            logger.error(f"JIT adapter tick failed: {e}", exc_info=True)
            return {
                'action': 'error',
                'error': str(e),
                'latency_ms': (time.time() - tick_start) * 1000
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive stats from JIT engine and adapter"""
        jit_stats = self.jit_engine._metrics.get_stats()
        
        return {
            'jit_engine': jit_stats,
            'last_quote_time': self._last_quote_time,
            'time_since_last_quote': time.time() - self._last_quote_time if self._last_quote_time > 0 else 0,
            'adapter_version': '3.0.0'
        }
