#!/usr/bin/env python3
"""
Swift Driver for Live Trend Bot Execution
Handles order placement via Swift sidecar with proper error handling
"""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import httpx

logger = logging.getLogger(__name__)

class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop_market"

@dataclass
class SwiftOrder:
    """Swift order representation"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    notional_usd: float
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    post_only: bool = False
    reduce_only: bool = False

class SwiftDriver:
    """
    Swift Sidecar Driver for Live Trading
    
    Handles:
    - Order placement via Swift HTTP API
    - Order status monitoring
    - Error handling and retries
    - Dry run mode for testing
    """
    
    def __init__(self, 
                 base_url: str = "http://localhost:8080",
                 timeout_seconds: float = 3.0,
                 dry_run: bool = True,
                 max_retries: int = 3):
        """
        Initialize Swift driver
        
        Args:
            base_url: Swift sidecar base URL
            timeout_seconds: HTTP timeout
            dry_run: Enable dry run mode (no real orders)
            max_retries: Maximum retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self.dry_run = dry_run
        self.max_retries = max_retries
        
        # Order tracking
        self._order_counter = 0
        self._active_orders: Dict[str, SwiftOrder] = {}
        
        logger.info(f"SwiftDriver initialized: {base_url} (dry_run={dry_run})")

    async def place_order(self, order: SwiftOrder) -> Optional[str]:
        """
        Place order via Swift sidecar
        
        Args:
            order: Swift order to place
            
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            if self.dry_run:
                return await self._place_dry_run_order(order)
            else:
                return await self._place_live_order(order)
                
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None

    async def _place_dry_run_order(self, order: SwiftOrder) -> str:
        """Place order in dry run mode"""
        self._order_counter += 1
        order_id = f"dry-{self._order_counter}"
        
        self._active_orders[order_id] = order
        
        logger.info(f"[DRY] ORDER PLACED: {order_id}")
        logger.info(f"[DRY]   Symbol: {order.symbol}")
        logger.info(f"[DRY]   Side: {order.side.value}")
        logger.info(f"[DRY]   Type: {order.order_type.value}")
        logger.info(f"[DRY]   Notional: ${order.notional_usd:.2f}")
        if order.limit_price:
            logger.info(f"[DRY]   Limit Price: ${order.limit_price:.4f}")
        if order.stop_price:
            logger.info(f"[DRY]   Stop Price: ${order.stop_price:.4f}")
        
        return order_id

    async def _place_live_order(self, order: SwiftOrder) -> Optional[str]:
        """Place live order via Swift sidecar"""
        payload = {
            "symbol": order.symbol,
            "side": order.side.value,
            "type": order.order_type.value,
            "notional_usd": order.notional_usd,
            "post_only": order.post_only,
            "reduce_only": order.reduce_only
        }
        
        if order.limit_price is not None:
            payload["limit_price"] = order.limit_price
        if order.stop_price is not None:
            payload["stop_price"] = order.stop_price
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/orders",
                        json=payload
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    order_id = result.get("id") or result.get("order_id")
                    
                    if order_id:
                        self._active_orders[str(order_id)] = order
                        logger.info(f"[LIVE] ORDER PLACED: {order_id} - {order.side.value} {order.notional_usd:.2f} USD")
                        return str(order_id)
                    else:
                        logger.error(f"No order ID in response: {result}")
                        return None
                        
            except httpx.TimeoutException:
                logger.warning(f"Order placement timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error placing order: {e.response.status_code} - {e.response.text}")
                break
                
            except Exception as e:
                logger.error(f"Unexpected error placing order: {e}")
                break
        
        return None

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel order by ID
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if successful
        """
        try:
            if self.dry_run:
                return await self._cancel_dry_run_order(order_id)
            else:
                return await self._cancel_live_order(order_id)
                
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def _cancel_dry_run_order(self, order_id: str) -> bool:
        """Cancel order in dry run mode"""
        if order_id in self._active_orders:
            del self._active_orders[order_id]
            logger.info(f"[DRY] ORDER CANCELLED: {order_id}")
            return True
        else:
            logger.warning(f"[DRY] Order not found for cancellation: {order_id}")
            return False

    async def _cancel_live_order(self, order_id: str) -> bool:
        """Cancel live order via Swift sidecar"""
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/orders/{order_id}/cancel"
                    )
                    response.raise_for_status()
                    
                    if order_id in self._active_orders:
                        del self._active_orders[order_id]
                    
                    logger.info(f"[LIVE] ORDER CANCELLED: {order_id}")
                    return True
                    
            except httpx.TimeoutException:
                logger.warning(f"Cancel timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error cancelling order: {e.response.status_code}")
                break
                
            except Exception as e:
                logger.error(f"Unexpected error cancelling order: {e}")
                break
        
        return False

    async def get_order_status(self, order_ids: List[str]) -> Dict[str, str]:
        """
        Get status of multiple orders
        
        Args:
            order_ids: List of order IDs to check
            
        Returns:
            Dictionary mapping order_id -> status
        """
        if self.dry_run:
            return await self._get_dry_run_status(order_ids)
        else:
            return await self._get_live_status(order_ids)

    async def _get_dry_run_status(self, order_ids: List[str]) -> Dict[str, str]:
        """Get order status in dry run mode"""
        status = {}
        for order_id in order_ids:
            if order_id in self._active_orders:
                # Simulate some orders filling randomly
                if hash(order_id + str(int(time.time() / 10))) % 20 == 0:
                    status[order_id] = "filled"
                    if order_id in self._active_orders:
                        del self._active_orders[order_id]
                else:
                    status[order_id] = "open"
            else:
                status[order_id] = "unknown"
        return status

    async def _get_live_status(self, order_ids: List[str]) -> Dict[str, str]:
        """Get live order status via Swift sidecar"""
        if not order_ids:
            return {}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {"ids": ",".join(order_ids)}
                response = await client.get(
                    f"{self.base_url}/orders/status",
                    params=params
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Parse response format
                status = {}
                filled_orders = result.get("filled", [])
                open_orders = result.get("open", [])
                
                for order_id in order_ids:
                    if order_id in filled_orders:
                        status[order_id] = "filled"
                        # Remove from active tracking
                        if order_id in self._active_orders:
                            del self._active_orders[order_id]
                    elif order_id in open_orders:
                        status[order_id] = "open"
                    else:
                        status[order_id] = "unknown"
                
                return status
                
        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
            return {order_id: "unknown" for order_id in order_ids}

    async def cancel_all_orders(self) -> int:
        """
        Cancel all active orders
        
        Returns:
            Number of orders successfully cancelled
        """
        active_order_ids = list(self._active_orders.keys())
        cancelled_count = 0
        
        for order_id in active_order_ids:
            if await self.cancel_order(order_id):
                cancelled_count += 1
        
        logger.info(f"Cancelled {cancelled_count}/{len(active_order_ids)} orders")
        return cancelled_count

    def get_active_orders(self) -> Dict[str, SwiftOrder]:
        """Get currently active orders"""
        return self._active_orders.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get driver statistics"""
        return {
            "base_url": self.base_url,
            "dry_run": self.dry_run,
            "active_orders": len(self._active_orders),
            "total_orders": self._order_counter,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Swift sidecar health
        
        Returns:
            Health status dictionary
        """
        health = {
            "timestamp": time.time(),
            "base_url": self.base_url,
            "dry_run": self.dry_run,
            "status": "unknown",
            "response_time_ms": None,
            "error": None
        }
        
        if self.dry_run:
            health["status"] = "healthy_dry_run"
            health["response_time_ms"] = 0
            return health
        
        try:
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                
                response_time = (time.time() - start_time) * 1000
                health["response_time_ms"] = round(response_time, 2)
                health["status"] = "healthy"
                
        except httpx.TimeoutException:
            health["status"] = "timeout"
            health["error"] = "Health check timeout"
        except httpx.HTTPStatusError as e:
            health["status"] = "http_error"
            health["error"] = f"HTTP {e.response.status_code}"
        except Exception as e:
            health["status"] = "error"
            health["error"] = str(e)
        
        return health

# Factory function for easy creation
def create_swift_driver(base_url: str = None, dry_run: bool = None) -> SwiftDriver:
    """
    Factory function to create Swift driver with environment defaults
    
    Args:
        base_url: Override base URL
        dry_run: Override dry run mode
        
    Returns:
        Configured SwiftDriver instance
    """
    import os
    
    if base_url is None:
        base_url = os.getenv("SWIFT_FORWARD_BASE", "http://localhost:8080")
    
    if dry_run is None:
        dry_run = int(os.getenv("DRY_RUN", "1")) == 1
    
    return SwiftDriver(base_url=base_url, dry_run=dry_run)



