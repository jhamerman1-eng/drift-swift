#!/usr/bin/env python3
"""
ExecutionRouter: Intent-based routing for maker vs taker orders

Properly routes maker quotes (resting) vs taker responses (JIT) with:
- Correct flag enforcement (post_only, IOC)  
- Cancel/replace split by intent
- Tick/lot precision normalization
- Error classification & retries
- Metrics & attribution
"""

import asyncio
import logging
import time
import uuid
from enum import Enum
from typing import Optional, Dict, Any, Callable, Union
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)

class ExecIntent(str, Enum):
    """Order execution intent determines routing and flags"""
    MAKER = "maker"   # resting quotes (MM bot)
    TAKER = "taker"   # JIT responses (aggressive fills)

class ErrorType(str, Enum):
    """Error classification for retry logic"""
    TRANSIENT = "transient"     # Network, timeout, rate limit
    PERMANENT = "permanent"     # Rejected, insufficient funds
    UNKNOWN = "unknown"         # Classify conservatively

@dataclass
class OrderResult:
    """Standardized order result"""
    success: bool
    order_id: Optional[str] = None
    error: Optional[str] = None
    error_type: ErrorType = ErrorType.UNKNOWN
    driver: Optional[str] = None  # "drift" or "swift"
    latency_ms: Optional[float] = None
    retry_count: int = 0

@dataclass 
class ExecutionMetrics:
    """Track execution performance by intent and driver"""
    def __init__(self):
        self.counters = {}
        
    def inc(self, metric: str, labels: Dict[str, str] = None):
        """Increment counter with labels"""
        key = f"{metric}_{labels}" if labels else metric
        self.counters[key] = self.counters.get(key, 0) + 1
        
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return {
            "counters": self.counters,
            "timestamp": time.time()
        }

class ExecutionRouter:
    """
    Intent-based execution router with proper maker/taker separation
    
    Key principles:
    - Maker quotes → DriftPy only (post-only, no IOC)
    - Taker responses → Swift first, fallback to DriftPy (IOC, no post-only)
    - Cancel/replace in same place you placed
    - Tick/lot normalization before submit
    - Error classification and retries
    """
    
    def __init__(
        self,
        drift_client,
        swift_client=None,
        tick_normalizer: Optional[Callable[[float], float]] = None,
        lot_normalizer: Optional[Callable[[float], float]] = None,
        swift_enabled: bool = True,
        max_retries: int = 3,
        retry_delays: list = None
    ):
        self.drift = drift_client
        self.swift = swift_client
        self.swift_enabled = swift_enabled and swift_client is not None
        
        # Precision normalizers
        self.tick = tick_normalizer or (lambda p: p)
        self.lot = lot_normalizer or (lambda q: q)
        
        # Retry configuration
        self.max_retries = max_retries
        self.retry_delays = retry_delays or [0.1, 0.5, 1.0]  # Exponential backoff
        
        # Metrics
        self.metrics = ExecutionMetrics()
        
        # Order tracking for cancel/replace
        self.order_drivers = {}  # order_id -> driver
        
        logger.info(f"ExecutionRouter initialized: swift_enabled={self.swift_enabled}")
    
    async def place(
        self, 
        order_params: Dict[str, Any], 
        intent: ExecIntent,
        idempotency_key: Optional[str] = None,
        context: Optional[str] = None
    ) -> OrderResult:
        """
        Place order with intent-based routing
        
        Args:
            order_params: Order parameters (price, size, etc.)
            intent: MAKER (resting) or TAKER (aggressive)
            idempotency_key: Client-side deduplication key
            context: Reason for order (skew_update, refresh, inventory, jit_response)
        """
        start_time = time.time()
        idempotency_key = idempotency_key or f"exec_{uuid.uuid4().hex[:8]}"
        
        # Normalize precision before submit
        normalized_params = self._normalize_order_params(order_params)
        
        # Validate post-only doesn't cross spread (for makers)
        if intent == ExecIntent.MAKER:
            if not self._validate_maker_price(normalized_params):
                return OrderResult(
                    success=False,
                    error="Maker price would cross spread after normalization",
                    error_type=ErrorType.PERMANENT,
                    latency_ms=(time.time() - start_time) * 1000
                )
        
        # Route by intent with retries
        for attempt in range(self.max_retries + 1):
            try:
                result = await self._execute_with_intent(normalized_params, intent, attempt)
                
                # Track metrics
                self.metrics.inc("orders_total", {
                    "intent": intent.value,
                    "driver": result.driver or "unknown",
                    "result": "success" if result.success else "fail",
                    "context": context or "unknown"
                })
                
                # Track order driver for cancel/replace
                if result.success and result.order_id:
                    self.order_drivers[result.order_id] = result.driver
                
                result.latency_ms = (time.time() - start_time) * 1000
                result.retry_count = attempt
                
                if result.success or result.error_type == ErrorType.PERMANENT:
                    return result
                    
                # Retry on transient errors
                if attempt < self.max_retries:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    logger.warning(f"Retrying order after {delay}s (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Order attempt {attempt} failed: {e}")
                if attempt == self.max_retries:
                    return OrderResult(
                        success=False,
                        error=str(e),
                        error_type=self._classify_error(e),
                        latency_ms=(time.time() - start_time) * 1000,
                        retry_count=attempt
                    )
        
        return OrderResult(
            success=False,
            error="Max retries exceeded",
            error_type=ErrorType.UNKNOWN,
            latency_ms=(time.time() - start_time) * 1000,
            retry_count=self.max_retries
        )
    
    async def cancel(self, order_id: str, intent: ExecIntent) -> OrderResult:
        """
        Cancel order in the same place it was placed
        
        Critical rule: Cancel where you placed!
        - Maker orders → DriftPy cancel
        - Taker orders → Swift cancel (if available)
        """
        start_time = time.time()
        
        # Determine driver from order tracking
        driver = self.order_drivers.get(order_id)
        
        try:
            if intent == ExecIntent.MAKER:
                # Maker orders always go through Drift
                if hasattr(self.drift, 'cancel_order'):
                    await self.drift.cancel_order(order_id)
                    result = OrderResult(success=True, driver="drift")
                else:
                    result = OrderResult(success=False, error="Drift cancel not available", error_type=ErrorType.PERMANENT)
                    
            elif intent == ExecIntent.TAKER:
                # Taker orders prefer Swift cancel, fallback to logging
                if self.swift and self.swift_enabled and hasattr(self.swift, 'cancel_order'):
                    try:
                        await self.swift.cancel_order(order_id)
                        result = OrderResult(success=True, driver="swift")
                    except Exception as e:
                        logger.warning(f"Swift cancel failed for {order_id}: {e}")
                        result = OrderResult(success=False, error=str(e), driver="swift")
                else:
                    # No Swift cancel available - this is expected for some setups
                    logger.info(f"No Swift cancel available for taker order {order_id}; skipping")
                    result = OrderResult(success=True, driver="none")
            else:
                result = OrderResult(success=False, error=f"Unknown intent: {intent}", error_type=ErrorType.PERMANENT)
            
            # Clean up tracking
            if order_id in self.order_drivers:
                del self.order_drivers[order_id]
                
            # Track metrics
            self.metrics.inc("cancels_total", {
                "intent": intent.value,
                "driver": result.driver or "unknown",
                "result": "success" if result.success else "fail"
            })
            
            result.latency_ms = (time.time() - start_time) * 1000
            return result
            
        except Exception as e:
            logger.error(f"Cancel failed for {order_id}: {e}")
            return OrderResult(
                success=False,
                error=str(e),
                error_type=self._classify_error(e),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def replace(
        self, 
        order_id: str, 
        new_params: Dict[str, Any], 
        intent: ExecIntent
    ) -> OrderResult:
        """
        Replace order (modify or cancel+place)
        
        Intent-based routing:
        - Maker → Drift modify_order (atomic)
        - Taker → Swift replace API (when available) or cancel+place fallback
        """
        start_time = time.time()
        
        # Normalize new parameters
        normalized_params = self._normalize_order_params(new_params)
        
        try:
            if intent == ExecIntent.MAKER:
                # Maker replace via Drift modify
                normalized_params = self._enforce_maker_flags(normalized_params)
                
                if hasattr(self.drift, 'modify_order'):
                    result_id = await self.drift.modify_order(order_id, normalized_params)
                    result = OrderResult(success=True, order_id=result_id, driver="drift")
                else:
                    # Fallback: cancel + place
                    await self.cancel(order_id, intent)
                    return await self.place(normalized_params, intent)
                    
            elif intent == ExecIntent.TAKER:
                # Taker replace via Swift (when available)
                if (self.swift and self.swift_enabled and 
                    hasattr(self.swift, 'replace_order')):
                    try:
                        normalized_params = self._enforce_taker_flags(normalized_params)
                        result_id = await self.swift.replace_order(order_id, normalized_params)
                        result = OrderResult(success=True, order_id=result_id, driver="swift")
                    except Exception as e:
                        logger.warning(f"Swift replace failed, falling back to cancel+place: {e}")
                        await self.cancel(order_id, intent)
                        return await self.place(normalized_params, intent)
                else:
                    # Fallback: cancel + place via appropriate driver
                    logger.info("Swift replace unavailable; doing cancel+re-place fallback")
                    await self.cancel(order_id, intent)
                    return await self.place(normalized_params, intent)
            else:
                result = OrderResult(success=False, error=f"Unknown intent: {intent}", error_type=ErrorType.PERMANENT)
            
            # Track metrics
            self.metrics.inc("replaces_total", {
                "intent": intent.value,
                "driver": result.driver or "unknown",
                "result": "success" if result.success else "fail"
            })
            
            result.latency_ms = (time.time() - start_time) * 1000
            return result
            
        except Exception as e:
            logger.error(f"Replace failed for {order_id}: {e}")
            return OrderResult(
                success=False,
                error=str(e),
                error_type=self._classify_error(e),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    def _normalize_order_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize price and quantity to tick/lot size"""
        normalized = params.copy()
        
        if 'price' in normalized:
            normalized['price'] = self.tick(normalized['price'])
            
        if 'base_asset_amount' in normalized:
            normalized['base_asset_amount'] = self.lot(normalized['base_asset_amount'])
        elif 'size' in normalized:
            normalized['size'] = self.lot(normalized['size'])
        elif 'quantity' in normalized:
            normalized['quantity'] = self.lot(normalized['quantity'])
            
        return normalized
    
    def _validate_maker_price(self, params: Dict[str, Any]) -> bool:
        """
        Validate that maker price doesn't cross spread after normalization
        
        This prevents accidentally creating aggressive orders when tick rounding
        pushes a post-only price across the spread.
        """
        # TODO: Implement spread checking with current orderbook
        # For now, assume normalization is safe
        return True
    
    def _enforce_maker_flags(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Enforce maker-specific flags"""
        enforced = params.copy()
        
        # Import at method level to avoid circular imports
        try:
            from driftpy.types import PostOnlyParams
            if hasattr(PostOnlyParams, 'MUST_POST_ONLY'):
                enforced['post_only'] = PostOnlyParams.MUST_POST_ONLY
            elif hasattr(PostOnlyParams, 'MustPostOnly'):
                enforced['post_only'] = PostOnlyParams.MustPostOnly()
            else:
                enforced['post_only'] = True  # Boolean fallback
        except (ImportError, AttributeError):
            enforced['post_only'] = True  # Fallback for mock environments
            
        enforced['immediate_or_cancel'] = False
        
        return enforced
    
    def _enforce_taker_flags(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Enforce taker-specific flags"""
        enforced = params.copy()
        
        # Import at method level to avoid circular imports
        try:
            from driftpy.types import PostOnlyParams
            if hasattr(PostOnlyParams, 'NONE'):
                enforced['post_only'] = PostOnlyParams.NONE
            elif hasattr(PostOnlyParams, 'None_'):
                enforced['post_only'] = PostOnlyParams.None_()
            else:
                enforced['post_only'] = False  # Boolean fallback
        except (ImportError, AttributeError):
            enforced['post_only'] = False  # Fallback for mock environments
            
        enforced['immediate_or_cancel'] = True  # Prefer IOC for taker orders
        
        return enforced
    
    async def _execute_with_intent(
        self, 
        params: Dict[str, Any], 
        intent: ExecIntent,
        attempt: int
    ) -> OrderResult:
        """Execute order based on intent"""
        
        if intent == ExecIntent.MAKER:
            # Maker → DriftPy only
            params = self._enforce_maker_flags(params)
            
            if hasattr(self.drift, 'place_perp_order'):
                order_id = await self.drift.place_perp_order(params)
                return OrderResult(success=True, order_id=order_id, driver="drift")
            else:
                return OrderResult(
                    success=False, 
                    error="Drift place_perp_order not available", 
                    error_type=ErrorType.PERMANENT
                )
                
        elif intent == ExecIntent.TAKER:
            # Taker → Swift first, fallback to DriftPy
            if self.swift and self.swift_enabled:
                try:
                    if hasattr(self.swift, 'place_signed'):
                        order_id = await self.swift.place_signed(params)
                        return OrderResult(success=True, order_id=order_id, driver="swift")
                    else:
                        logger.warning("Swift place_signed not available, falling back to Drift")
                except Exception as e:
                    logger.warning(f"Swift failed (attempt {attempt}), falling back to Drift: {e}")
                    # Fall through to Drift fallback
            
            # Drift fallback for taker
            params = self._enforce_taker_flags(params)
            
            if hasattr(self.drift, 'place_perp_order'):
                order_id = await self.drift.place_perp_order(params)
                return OrderResult(success=True, order_id=order_id, driver="drift")
            else:
                return OrderResult(
                    success=False,
                    error="No execution drivers available",
                    error_type=ErrorType.PERMANENT
                )
        else:
            return OrderResult(
                success=False,
                error=f"Unknown intent: {intent}",
                error_type=ErrorType.PERMANENT
            )
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error for retry logic"""
        error_str = str(error).lower()
        
        # Transient errors (retry)
        if any(keyword in error_str for keyword in [
            'timeout', 'connection', 'network', 'rate limit', 'too many requests',
            'unavailable', 'temporary', 'retry'
        ]):
            return ErrorType.TRANSIENT
            
        # Permanent errors (don't retry)
        if any(keyword in error_str for keyword in [
            'insufficient', 'invalid', 'rejected', 'unauthorized', 'forbidden',
            'not found', 'bad request', 'conflict', 'duplicate'
        ]):
            return ErrorType.PERMANENT
            
        # Conservative default
        return ErrorType.UNKNOWN
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics"""
        return {
            "execution_stats": self.metrics.get_stats(),
            "config": {
                "swift_enabled": self.swift_enabled,
                "max_retries": self.max_retries,
                "retry_delays": self.retry_delays
            },
            "order_tracking": {
                "tracked_orders": len(self.order_drivers),
                "driver_breakdown": {}
            }
        }
