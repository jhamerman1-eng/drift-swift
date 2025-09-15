#!/usr/bin/env python3
"""
Resilient WebSocket subscription utilities
Provides exponential backoff and auto-reconnection for WebSocket subscriptions
"""

import asyncio
import logging
from typing import Callable, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class BackoffConfig:
    """Configuration for exponential backoff"""
    initial_delay: float = 1.0
    max_delay: float = 30.0
    multiplier: float = 2.0
    jitter: bool = True

class ResilientSubscription:
    """Base class for resilient WebSocket subscriptions"""
    
    def __init__(self, name: str, backoff_config: Optional[BackoffConfig] = None):
        self.name = name
        self.backoff_config = backoff_config or BackoffConfig()
        self.running = False
        self.current_delay = self.backoff_config.initial_delay
        self._task: Optional[asyncio.Task] = None
    
    async def _apply_jitter(self, delay: float) -> float:
        """Apply jitter to prevent thundering herd"""
        if self.backoff_config.jitter:
            import random
            jitter_factor = random.uniform(0.5, 1.5)
            return delay * jitter_factor
        return delay
    
    def _calculate_next_delay(self) -> float:
        """Calculate next delay with exponential backoff"""
        self.current_delay = min(
            self.current_delay * self.backoff_config.multiplier,
            self.backoff_config.max_delay
        )
        return self.current_delay
    
    def _reset_delay(self):
        """Reset delay to initial value on successful connection"""
        self.current_delay = self.backoff_config.initial_delay

async def resilient_user_map_subscribe(user_map, name: str = "UserMap", 
                                     backoff_config: Optional[BackoffConfig] = None) -> ResilientSubscription:
    """
    Create a resilient UserMap subscription with exponential backoff
    
    Args:
        user_map: UserMap instance to subscribe
        name: Name for logging
        backoff_config: Backoff configuration
    
    Returns:
        ResilientSubscription instance
    """
    config = backoff_config or BackoffConfig()
    subscription = ResilientSubscription(name, config)
    
    async def _subscribe_loop():
        subscription.running = True
        while subscription.running:
            try:
                await user_map.subscribe()
                subscription._reset_delay()
                logger.info(f"[{name}] WebSocket connected successfully")
                
                # Wait indefinitely until connection drops
                await asyncio.Event().wait()
                
            except Exception as e:
                if subscription.running:
                    delay = subscription._calculate_next_delay()
                    jittered_delay = await subscription._apply_jitter(delay)
                    
                    logger.warning(f"[{name}] WebSocket dropped ({e}); retrying in {jittered_delay:.1f}s")
                    await asyncio.sleep(jittered_delay)
                else:
                    break
    
    subscription._task = asyncio.create_task(_subscribe_loop())
    return subscription

async def resilient_swift_subscribe(swift_sub, on_order_callback: Callable, 
                                  name: str = "Swift", 
                                  backoff_config: Optional[BackoffConfig] = None) -> ResilientSubscription:
    """
    Create a resilient Swift subscription with exponential backoff
    
    Args:
        swift_sub: Swift subscriber instance
        on_order_callback: Callback function for order processing
        name: Name for logging
        backoff_config: Backoff configuration
    
    Returns:
        ResilientSubscription instance
    """
    config = backoff_config or BackoffConfig()
    subscription = ResilientSubscription(name, config)
    
    async def _subscribe_loop():
        subscription.running = True
        while subscription.running:
            try:
                await swift_sub.subscribe(on_order_callback)
                subscription._reset_delay()
                logger.info(f"[{name}] Swift WebSocket connected successfully")
                
                # Wait indefinitely until connection drops
                await asyncio.Event().wait()
                
            except Exception as e:
                if subscription.running:
                    delay = subscription._calculate_next_delay()
                    jittered_delay = await subscription._apply_jitter(delay)
                    
                    logger.warning(f"[{name}] Swift WebSocket dropped ({e}); retrying in {jittered_delay:.1f}s")
                    await asyncio.sleep(jittered_delay)
                else:
                    break
    
    subscription._task = asyncio.create_task(_subscribe_loop())
    return subscription

async def stop_resilient_subscription(subscription: ResilientSubscription):
    """Stop a resilient subscription gracefully"""
    if subscription and subscription.running:
        subscription.running = False
        if subscription._task:
            subscription._task.cancel()
            try:
                await subscription._task
            except asyncio.CancelledError:
                pass
        logger.info(f"[{subscription.name}] Resilient subscription stopped")

class WebSocketHealthMonitor:
    """Monitor WebSocket connection health and provide stats"""
    
    def __init__(self):
        self.connection_attempts = 0
        self.successful_connections = 0
        self.failed_connections = 0
        self.last_connection_time = None
        self.last_failure_time = None
        self.current_delay = 1.0
    
    def record_connection_attempt(self):
        """Record a connection attempt"""
        self.connection_attempts += 1
    
    def record_successful_connection(self):
        """Record a successful connection"""
        self.successful_connections += 1
        self.last_connection_time = asyncio.get_event_loop().time()
        self.current_delay = 1.0  # Reset delay on success
    
    def record_failed_connection(self, error: Exception):
        """Record a failed connection"""
        self.failed_connections += 1
        self.last_failure_time = asyncio.get_event_loop().time()
    
    def get_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "connection_attempts": self.connection_attempts,
            "successful_connections": self.successful_connections,
            "failed_connections": self.failed_connections,
            "success_rate": (
                self.successful_connections / self.connection_attempts 
                if self.connection_attempts > 0 else 0
            ),
            "last_connection_time": self.last_connection_time,
            "last_failure_time": self.last_failure_time,
            "current_delay": self.current_delay
        }





