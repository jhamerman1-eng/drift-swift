#!/usr/bin/env python3
"""
Redis Client Wrapper for Drift Bots

Provides a configured Redis client with connection pooling, health checks,
and caching utilities optimized for the PythLazerSubscriber.
"""

import json
import logging
from typing import Optional, Any, Dict, Union
from dataclasses import dataclass

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from ..config import get_redis_config

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a cached item with metadata"""
    data: Any
    timestamp: float
    ttl: int

class DriftRedisClient:
    """
    Redis client wrapper optimized for Drift caching needs.

    Features:
    - Connection pooling with health checks
    - Automatic key prefixing
    - TTL management
    - JSON serialization/deserialization
    - Graceful degradation when Redis unavailable
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Redis client with configuration

        Args:
            config: Redis configuration dict, if None uses environment config
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis package not available, caching disabled")
            self.client = None
            self.config = {}
            return

        self.config = config or get_redis_config()

        if not self.config.get("enabled", True):
            logger.info("Redis disabled in configuration")
            self.client = None
            return

        try:
            self.client = redis.Redis(
                host=self.config["host"],
                port=self.config["port"],
                db=self.config["db"],
                password=self.config["password"] or None,
                socket_timeout=self.config["socket_timeout"],
                socket_connect_timeout=self.config["socket_connect_timeout"],
                socket_keepalive=self.config["socket_keepalive"],
                socket_keepalive_options=self.config["socket_keepalive_options"],
                health_check_interval=self.config["health_check_interval"],
                max_connections=self.config["max_connections"],
                retry_on_timeout=self.config["retry_on_timeout"],
                decode_responses=self.config["decode_responses"]
            )
            logger.info(f"Redis client initialized: {self.config['host']}:{self.config['port']}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            self.client = None

    def _make_key(self, key: str) -> str:
        """Add prefix to key"""
        prefix = self.config.get("key_prefix", "")
        return f"{prefix}{key}"

    async def is_connected(self) -> bool:
        """Check if Redis is connected and responding"""
        if not self.client:
            return False

        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in Redis with optional TTL

        Args:
            key: Cache key (will be prefixed)
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds, if None uses config default

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False

        try:
            full_key = self._make_key(key)
            ttl_value = ttl or self.config.get("ttl_seconds", 300)

            # Create cache entry with metadata
            entry = CacheEntry(
                data=value,
                timestamp=self._current_time(),
                ttl=ttl_value
            )

            json_data = json.dumps({
                "data": entry.data,
                "timestamp": entry.timestamp,
                "ttl": entry.ttl
            })

            await self.client.setex(full_key, ttl_value, json_data)
            return True

        except Exception as e:
            logger.warning(f"Redis set failed for key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis

        Args:
            key: Cache key (will be prefixed)

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if not self.client:
            return None

        try:
            full_key = self._make_key(key)
            data = await self.client.get(full_key)

            if not data:
                return None

            # Parse cache entry
            parsed = json.loads(data)
            entry = CacheEntry(**parsed)

            # Check if entry has expired
            age = self._current_time() - entry.timestamp
            if age > entry.ttl:
                # Entry expired, remove it
                await self.client.delete(full_key)
                return None

            return entry.data

        except Exception as e:
            logger.warning(f"Redis get failed for key {key}: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key from Redis"""
        if not self.client:
            return False

        try:
            full_key = self._make_key(key)
            await self.client.delete(full_key)
            return True
        except Exception as e:
            logger.warning(f"Redis delete failed for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis"""
        if not self.client:
            return False

        try:
            full_key = self._make_key(key)
            return await self.client.exists(full_key) > 0
        except Exception as e:
            logger.warning(f"Redis exists check failed for key {key}: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """Get TTL for a key in seconds"""
        if not self.client:
            return -1

        try:
            full_key = self._make_key(key)
            return await self.client.ttl(full_key)
        except Exception as e:
            logger.warning(f"Redis TTL check failed for key {key}: {e}")
            return -1

    async def clear_prefix(self, prefix: str) -> int:
        """Clear all keys with a specific prefix"""
        if not self.client:
            return 0

        try:
            # Use SCAN to find keys with prefix
            pattern = f"{self._make_key(prefix)}*"
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self.client.delete(*keys)

            logger.info(f"Cleared {len(keys)} keys with prefix {prefix}")
            return len(keys)

        except Exception as e:
            logger.warning(f"Redis clear_prefix failed for {prefix}: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        if not self.client:
            return {"status": "disabled"}

        try:
            info = await self.client.info()
            return {
                "status": "connected",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "total_connections_received": info.get("total_connections_received", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.warning(f"Failed to get Redis stats: {e}")
            return {"status": "error", "error": str(e)}

    def _current_time(self) -> float:
        """Get current time for TTL calculations"""
        import time
        return time.time()

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

# Global instance for easy access
_redis_client = None

def get_redis_client() -> DriftRedisClient:
    """Get global Redis client instance"""
    global _redis_client
    if _redis_client is None:
        _redis_client = DriftRedisClient()
    return _redis_client

# Convenience functions for common operations
async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set a value in cache"""
    return await get_redis_client().set(key, value, ttl)

async def cache_get(key: str) -> Optional[Any]:
    """Get a value from cache"""
    return await get_redis_client().get(key)

async def cache_exists(key: str) -> bool:
    """Check if key exists in cache"""
    return await get_redis_client().exists(key)

async def cache_delete(key: str) -> bool:
    """Delete a key from cache"""
    return await get_redis_client().delete(key)
