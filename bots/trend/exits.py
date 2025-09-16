#!/usr/bin/env python3
"""
OCO Stop Emulation for Trend Bot v3.0
Implements synthetic stop-loss and take-profit orders

This module provides OCO (One-Cancels-Other) functionality for Drift Protocol
since native OCO orders are not available. Uses order tracking and cancel/replace
to emulate stop-loss and take-profit behavior.

User Story: TREND-007
Persona: Trader
Goal: Automated stop/target enforcement without native OCO support
"""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Order status tracking"""
    PENDING = "pending"
    ACTIVE = "active"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"

class StopType(Enum):
    """Stop order types"""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

@dataclass
class OCOOrder:
    """Individual order in OCO pair"""
    order_id: str
    side: str  # "buy" or "sell"
    price: float
    size: float
    stop_type: StopType
    status: OrderStatus = OrderStatus.PENDING
    created_at: float = field(default_factory=time.time)
    filled_at: Optional[float] = None

@dataclass
class OCOPair:
    """OCO order pair (stop + target)"""
    entry_order_id: str
    entry_side: str
    entry_price: float
    entry_size: float
    stop_order: Optional[OCOOrder] = None
    target_order: Optional[OCOOrder] = None
    created_at: float = field(default_factory=time.time)
    is_active: bool = True

class OCOManager:
    """
    OCO Stop Emulation Manager
    
    Manages synthetic stop-loss and take-profit orders by:
    1. Creating opposite-side orders at calculated prices
    2. Monitoring for fills via order status polling
    3. Cancelling the remaining order when one fills
    4. Handling order rejections and errors
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OCO manager with configuration
        
        Args:
            config: Configuration dictionary with OCO settings
        """
        oco_cfg = config.get("oco", {})
        
        # OCO behavior settings
        self.max_slippage_bps = float(oco_cfg.get("max_slippage_bps", 10.0))  # 10bps max slippage
        self.poll_interval_seconds = float(oco_cfg.get("poll_interval_seconds", 2.0))
        self.max_order_age_seconds = float(oco_cfg.get("max_order_age_seconds", 3600))  # 1 hour
        self.retry_failed_orders = bool(oco_cfg.get("retry_failed_orders", True))
        self.use_post_only = bool(oco_cfg.get("use_post_only", True))
        
        # Order tracking
        self.active_pairs: Dict[str, OCOPair] = {}
        self.completed_pairs: List[OCOPair] = []
        
        logger.info("OCO Manager initialized:")
        logger.info(f"  Max slippage: {self.max_slippage_bps:.1f} bps")
        logger.info(f"  Poll interval: {self.poll_interval_seconds:.1f}s")
        logger.info(f"  Use post-only: {self.use_post_only}")

    async def create_oco_pair(self, 
                            drift_client,
                            entry_order_id: str,
                            entry_side: str,
                            entry_price: float,
                            entry_size: float,
                            stop_loss_pct: float,
                            take_profit_pct: float) -> Optional[str]:
        """
        Create OCO stop-loss and take-profit orders
        
        Args:
            drift_client: Drift client for order placement
            entry_order_id: ID of the entry order
            entry_side: "buy" or "sell"
            entry_price: Entry price
            entry_size: Position size
            stop_loss_pct: Stop loss percentage (e.g., 0.01 for 1%)
            take_profit_pct: Take profit percentage (e.g., 0.02 for 2%)
            
        Returns:
            OCO pair ID if successful, None otherwise
        """
        try:
            # Generate unique pair ID
            pair_id = f"oco-{int(time.time() * 1000)}-{len(self.active_pairs)}"
            
            # Calculate stop and target prices
            if entry_side.lower() == "buy":
                # Long position: stop below entry, target above
                stop_price = entry_price * (1.0 - stop_loss_pct)
                target_price = entry_price * (1.0 + take_profit_pct)
                exit_side = "sell"
            else:
                # Short position: stop above entry, target below
                stop_price = entry_price * (1.0 + stop_loss_pct)
                target_price = entry_price * (1.0 - take_profit_pct)
                exit_side = "buy"
            
            logger.info(f"Creating OCO pair {pair_id}:")
            logger.info(f"  Entry: {entry_side} {entry_size:.4f} @ ${entry_price:.4f}")
            logger.info(f"  Stop: {exit_side} @ ${stop_price:.4f} (-{stop_loss_pct*100:.1f}%)")
            logger.info(f"  Target: {exit_side} @ ${target_price:.4f} (+{take_profit_pct*100:.1f}%)")
            
            # Create OCO pair object
            oco_pair = OCOPair(
                entry_order_id=entry_order_id,
                entry_side=entry_side,
                entry_price=entry_price,
                entry_size=entry_size
            )
            
            # Place stop-loss order
            try:
                stop_order_id = await self._place_stop_order(
                    drift_client, exit_side, stop_price, entry_size
                )
                if stop_order_id:
                    oco_pair.stop_order = OCOOrder(
                        order_id=stop_order_id,
                        side=exit_side,
                        price=stop_price,
                        size=entry_size,
                        stop_type=StopType.STOP_LOSS,
                        status=OrderStatus.ACTIVE
                    )
                    logger.info(f"Stop-loss order placed: {stop_order_id}")
            except Exception as e:
                logger.error(f"Failed to place stop-loss order: {e}")
            
            # Place take-profit order
            try:
                target_order_id = await self._place_limit_order(
                    drift_client, exit_side, target_price, entry_size
                )
                if target_order_id:
                    oco_pair.target_order = OCOOrder(
                        order_id=target_order_id,
                        side=exit_side,
                        price=target_price,
                        size=entry_size,
                        stop_type=StopType.TAKE_PROFIT,
                        status=OrderStatus.ACTIVE
                    )
                    logger.info(f"Take-profit order placed: {target_order_id}")
            except Exception as e:
                logger.error(f"Failed to place take-profit order: {e}")
            
            # Only activate if at least one order was placed
            if oco_pair.stop_order or oco_pair.target_order:
                self.active_pairs[pair_id] = oco_pair
                logger.info(f"OCO pair {pair_id} created successfully")
                return pair_id
            else:
                logger.error(f"Failed to create any OCO orders for pair {pair_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating OCO pair: {e}")
            return None

    async def _place_stop_order(self, drift_client, side: str, price: float, size: float) -> Optional[str]:
        """
        Place a stop-market order (emulated with market order trigger)
        
        Args:
            drift_client: Drift client
            side: "buy" or "sell"
            price: Stop trigger price
            size: Order size
            
        Returns:
            Order ID if successful
        """
        try:
            # Note: Since Drift may not have native stop orders, we emulate with limit orders
            # In practice, this would need monitoring to convert to market orders when triggered
            
            from driftpy.types import OrderParams, OrderType, MarketType, PositionDirection, PostOnlyParams
            
            direction = PositionDirection.Long() if side == "buy" else PositionDirection.Short()
            
            order_params = OrderParams(
                order_type=OrderType.Limit(),
                market_type=MarketType.Perp(),
                direction=direction,
                market_index=0,  # SOL-PERP
                base_asset_amount=int(size * 1e9),  # Convert to base precision
                price=int(price * 1e6),  # Convert to price precision
                user_order_id=int(time.time() * 1000) % 100000,
                post_only=PostOnlyParams.TryPostOnly() if self.use_post_only else PostOnlyParams.None_(),
                reduce_only=True,  # Stop orders should be reduce-only
            )
            
            # Place order via drift client
            if hasattr(drift_client, 'place_perp_order'):
                result = await drift_client.place_perp_order(order_params)
            else:
                # Fallback for different client interfaces
                result = await drift_client.place_order(order_params)
            
            return str(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to place stop order: {e}")
            return None

    async def _place_limit_order(self, drift_client, side: str, price: float, size: float) -> Optional[str]:
        """
        Place a limit order for take-profit
        
        Args:
            drift_client: Drift client
            side: "buy" or "sell"
            price: Limit price
            size: Order size
            
        Returns:
            Order ID if successful
        """
        try:
            from driftpy.types import OrderParams, OrderType, MarketType, PositionDirection, PostOnlyParams
            
            direction = PositionDirection.Long() if side == "buy" else PositionDirection.Short()
            
            order_params = OrderParams(
                order_type=OrderType.Limit(),
                market_type=MarketType.Perp(),
                direction=direction,
                market_index=0,  # SOL-PERP
                base_asset_amount=int(size * 1e9),  # Convert to base precision
                price=int(price * 1e6),  # Convert to price precision
                user_order_id=int(time.time() * 1000) % 100000,
                post_only=PostOnlyParams.MustPostOnly() if self.use_post_only else PostOnlyParams.None_(),
                reduce_only=True,  # Take-profit orders should be reduce-only
            )
            
            # Place order via drift client
            if hasattr(drift_client, 'place_perp_order'):
                result = await drift_client.place_perp_order(order_params)
            else:
                # Fallback for different client interfaces
                result = await drift_client.place_order(order_params)
            
            return str(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to place limit order: {e}")
            return None

    async def monitor_oco_pairs(self, drift_client) -> None:
        """
        Monitor active OCO pairs for fills and handle cancellations
        
        This should be called periodically (e.g., every 2 seconds) to:
        1. Check order statuses
        2. Cancel remaining orders when one fills
        3. Clean up completed pairs
        
        Args:
            drift_client: Drift client for order management
        """
        if not self.active_pairs:
            return
        
        logger.debug(f"Monitoring {len(self.active_pairs)} active OCO pairs")
        
        completed_pairs = []
        
        for pair_id, pair in self.active_pairs.items():
            try:
                # Check if orders are filled
                stop_filled = await self._check_order_filled(drift_client, pair.stop_order)
                target_filled = await self._check_order_filled(drift_client, pair.target_order)
                
                if stop_filled or target_filled:
                    logger.info(f"OCO pair {pair_id} triggered: "
                              f"stop_filled={stop_filled}, target_filled={target_filled}")
                    
                    # Cancel the remaining order
                    await self._cancel_remaining_orders(drift_client, pair, stop_filled, target_filled)
                    
                    # Mark pair as completed
                    pair.is_active = False
                    completed_pairs.append(pair_id)
                    self.completed_pairs.append(pair)
                    
                # Check for stale orders
                elif time.time() - pair.created_at > self.max_order_age_seconds:
                    logger.warning(f"OCO pair {pair_id} expired after {self.max_order_age_seconds}s")
                    await self._cancel_all_orders(drift_client, pair)
                    completed_pairs.append(pair_id)
                    
            except Exception as e:
                logger.error(f"Error monitoring OCO pair {pair_id}: {e}")
        
        # Remove completed pairs
        for pair_id in completed_pairs:
            self.active_pairs.pop(pair_id, None)
        
        if completed_pairs:
            logger.info(f"Cleaned up {len(completed_pairs)} completed OCO pairs")

    async def _check_order_filled(self, drift_client, order: Optional[OCOOrder]) -> bool:
        """
        Check if an order has been filled
        
        Args:
            drift_client: Drift client
            order: OCO order to check
            
        Returns:
            True if order is filled
        """
        if not order or order.status == OrderStatus.FILLED:
            return order is not None and order.status == OrderStatus.FILLED
        
        try:
            # Query order status from drift client
            # Note: Implementation depends on drift client interface
            if hasattr(drift_client, 'get_order'):
                order_info = await drift_client.get_order(order.order_id)
                if order_info and getattr(order_info, 'status', None) == 'filled':
                    order.status = OrderStatus.FILLED
                    order.filled_at = time.time()
                    return True
            
            # Fallback: check if order is still in open orders
            if hasattr(drift_client, 'get_open_orders'):
                open_orders = await drift_client.get_open_orders()
                order_ids = [str(o.order_id) for o in open_orders if hasattr(o, 'order_id')]
                if order.order_id not in order_ids:
                    # Order not in open orders - assume filled
                    order.status = OrderStatus.FILLED
                    order.filled_at = time.time()
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking order {order.order_id} status: {e}")
            return False

    async def _cancel_remaining_orders(self, drift_client, pair: OCOPair, stop_filled: bool, target_filled: bool):
        """
        Cancel the remaining order(s) when one leg of OCO fills
        
        Args:
            drift_client: Drift client
            pair: OCO pair
            stop_filled: Whether stop order filled
            target_filled: Whether target order filled
        """
        try:
            if stop_filled and pair.target_order and pair.target_order.status == OrderStatus.ACTIVE:
                logger.info(f"Stop filled, cancelling target order {pair.target_order.order_id}")
                await self._cancel_order(drift_client, pair.target_order)
            
            if target_filled and pair.stop_order and pair.stop_order.status == OrderStatus.ACTIVE:
                logger.info(f"Target filled, cancelling stop order {pair.stop_order.order_id}")
                await self._cancel_order(drift_client, pair.stop_order)
                
        except Exception as e:
            logger.error(f"Error cancelling remaining orders: {e}")

    async def _cancel_all_orders(self, drift_client, pair: OCOPair):
        """Cancel all orders in an OCO pair"""
        try:
            if pair.stop_order:
                await self._cancel_order(drift_client, pair.stop_order)
            if pair.target_order:
                await self._cancel_order(drift_client, pair.target_order)
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")

    async def _cancel_order(self, drift_client, order: OCOOrder):
        """Cancel a single order"""
        try:
            if hasattr(drift_client, 'cancel_order'):
                await drift_client.cancel_order(order.order_id)
            elif hasattr(drift_client, 'cancel_orders'):
                # Some clients have different interfaces
                await drift_client.cancel_orders(0)  # Cancel all for market 0
            
            order.status = OrderStatus.CANCELLED
            logger.debug(f"Cancelled order {order.order_id}")
            
        except Exception as e:
            logger.warning(f"Failed to cancel order {order.order_id}: {e}")

    def get_active_pairs_status(self) -> Dict[str, Any]:
        """Get status of all active OCO pairs for monitoring"""
        return {
            "active_count": len(self.active_pairs),
            "completed_count": len(self.completed_pairs),
            "pairs": {
                pair_id: {
                    "entry_side": pair.entry_side,
                    "entry_price": pair.entry_price,
                    "stop_order": {
                        "id": pair.stop_order.order_id if pair.stop_order else None,
                        "price": pair.stop_order.price if pair.stop_order else None,
                        "status": pair.stop_order.status.value if pair.stop_order else None
                    },
                    "target_order": {
                        "id": pair.target_order.order_id if pair.target_order else None,
                        "price": pair.target_order.price if pair.target_order else None,
                        "status": pair.target_order.status.value if pair.target_order else None
                    },
                    "age_seconds": time.time() - pair.created_at
                }
                for pair_id, pair in self.active_pairs.items()
            }
        }

    async def cleanup_all_pairs(self, drift_client):
        """Emergency cleanup - cancel all active OCO orders"""
        logger.warning(f"Emergency cleanup: cancelling {len(self.active_pairs)} active OCO pairs")
        
        for pair_id, pair in list(self.active_pairs.items()):
            try:
                await self._cancel_all_orders(drift_client, pair)
                self.completed_pairs.append(pair)
            except Exception as e:
                logger.error(f"Error during emergency cleanup of pair {pair_id}: {e}")
        
        self.active_pairs.clear()
        logger.info("Emergency cleanup completed")



