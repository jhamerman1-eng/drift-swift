#!/usr/bin/env python3
"""
PythLazerSubscriber: High-performance Pyth price feed subscriber

Features:
- WebSocket-based real-time price feeds
- HTTP fallback for single feed requests
- Redis caching for improved performance (optional dependency)
- Automatic resubscription on connection failures
- Support for multiple price feed chunks
- Price parsing and market index mapping
- Integration with Drift market configuration

Note: Redis support is optional. Install with: pip install redis==4.6.0
"""

import asyncio
import logging
import json
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

import aiohttp
import websockets

from ..config import get_pyth_config, get_redis_config
from ..cache.redis_client import DriftRedisClient, REDIS_AVAILABLE

logger = logging.getLogger(__name__)

class Channel(str, Enum):
    FIXED_RATE_200MS = "fixed_rate@200ms"
    REAL_TIME = "real_time"

@dataclass
class PythLazerPriceFeedArray:
    channel: Optional[Channel] = None
    price_feed_ids: Optional[List[int]] = None

    def __post_init__(self):
        if self.price_feed_ids is None:
            self.price_feed_ids = []

# Drift market configuration (simplified - would be imported from driftpy)
DRIFT_MARKETS = {
    "devnet": [
        {"market_index": 0, "pyth_lazer_id": 1},  # SOL/USD
        {"market_index": 1, "pyth_lazer_id": 2},  # BTC/USD
        # Add more markets as needed
    ],
    "mainnet-beta": [
        {"market_index": 0, "pyth_lazer_id": 1},  # SOL/USD
        {"market_index": 1, "pyth_lazer_id": 2},  # BTC/USD
        # Add more markets as needed
    ]
}

class PythLazerSubscriber:
    """
    High-performance subscriber for Pyth Lazer price feeds.

    Supports both WebSocket streaming and HTTP requests with automatic failover.
    Includes Redis caching and connection health monitoring.
    Integrates with Drift market configuration.
    """

    def __init__(
        self,
        drift_env: str = 'devnet',
        market_indexes: Optional[List[int]] = None,
        redis_client: Optional[DriftRedisClient] = None
    ):
        """
        Initialize PythLazerSubscriber with configuration from environment.

        Args:
            drift_env: Drift environment (devnet/mainnet-beta)
            market_indexes: Specific market indexes to subscribe to (None for all)
            redis_client: Optional Redis client for caching
        """
        # Load configuration from environment
        config = get_pyth_config()
        if not config["enabled"]:
            raise ValueError("Pyth configuration is disabled")

        self.endpoints = config["lazer_endpoints"]
        self.token = config["lazer_token"]
        self.http_endpoints = config["http_endpoints"]
        self.resub_timeout_ms = config["resub_timeout_ms"]
        self.chunk_size = config["chunk_size"]
        self.drift_env = drift_env

        # Initialize Redis client
        if redis_client:
            self.redis_client = redis_client
        elif REDIS_AVAILABLE:
            redis_config = get_redis_config()
            if redis_config.get("enabled", True):
                self.redis_client = DriftRedisClient(redis_config)
            else:
                self.redis_client = None
        else:
            logger.warning("Redis not available, caching disabled")
            self.redis_client = None

        # Data storage
        self.feed_id_chunk_to_price_message: Dict[str, str] = {}
        self.feed_id_to_price: Dict[int, float] = {}
        self.feed_id_hash_to_feed_ids: Dict[str, List[int]] = {}
        self.subscription_ids_to_feed_ids_hash: Dict[int, str] = {}
        self.all_subscribed_ids: List[int] = []

        # Connection management
        self.websocket: Optional[Any] = None  # WebSocket connection
        self.timeout_handle: Optional[asyncio.Task] = None
        self.receiving_data = False
        self.is_unsubscribing = False
        self.use_http_requests = False

        # Market mappings
        self.market_index_to_price_feed_id_chunk: Dict[int, List[int]] = {}
        self.market_index_to_price_feed_id: Dict[int, int] = {}

        # Setup market mappings and price feed arrays
        self.price_feed_arrays = self._setup_market_mappings(market_indexes)
        self._setup_feed_mappings()

    def _setup_market_mappings(self, market_indexes: Optional[List[int]]) -> List[PythLazerPriceFeedArray]:
        """Setup market mappings and create price feed arrays"""
        markets = DRIFT_MARKETS.get(self.drift_env, [])

        if not markets:
            logger.warning(f"No markets configured for environment: {self.drift_env}")
            return []

        # Filter markets if specific indexes requested
        if market_indexes is not None:
            markets = [m for m in markets if m["market_index"] in market_indexes]

        # Group markets into chunks for efficient subscription
        feed_ids = []
        for market in markets:
            feed_id = market.get("pyth_lazer_id")
            if feed_id is not None:
                feed_ids.append(feed_id)
                self.market_index_to_price_feed_id[market["market_index"]] = feed_id

        # Create chunks for subscription
        price_feed_arrays = []
        for i in range(0, len(feed_ids), self.chunk_size):
            chunk = feed_ids[i:i + self.chunk_size]
            price_feed_arrays.append(PythLazerPriceFeedArray(
                channel=Channel.FIXED_RATE_200MS,
                price_feed_ids=chunk
            ))

            # Map chunk to all markets in this chunk
            for market in markets:
                if market.get("pyth_lazer_id") in chunk:
                    self.market_index_to_price_feed_id_chunk[market["market_index"]] = chunk

        return price_feed_arrays

    def _setup_feed_mappings(self):
        """Setup feed ID mappings and determine subscription strategy"""
        self.all_subscribed_ids = [
            feed_id
            for array in self.price_feed_arrays
            for feed_id in (array.price_feed_ids or [])
        ]

        # Use HTTP requests for single feeds with many IDs (optimization)
        first_array = self.price_feed_arrays[0] if self.price_feed_arrays else None
        if (
            len(self.price_feed_arrays) > 0 and
            first_array and len(first_array.price_feed_ids or []) == 1 and
            len(self.all_subscribed_ids) > 3 and
            len(self.http_endpoints) > 0
        ):
            self.use_http_requests = True
            logger.info(f"Using HTTP requests for {len(self.all_subscribed_ids)} single feeds")

    async def subscribe(self):
        """Subscribe to price feeds via WebSocket or HTTP"""
        if self.use_http_requests:
            logger.info("Using HTTP requests for Pyth Lazer subscription")
            return

        await self._connect_websocket()

        subscription_id = 1
        for price_feed_array in self.price_feed_arrays:
            feed_ids = price_feed_array.price_feed_ids or []
            if feed_ids:
                feed_ids_hash = self._hash_feed_ids(feed_ids)
                self.feed_id_hash_to_feed_ids[feed_ids_hash] = feed_ids
                self.subscription_ids_to_feed_ids_hash[subscription_id] = feed_ids_hash
                await self._subscribe_to_feeds(subscription_id, price_feed_array)
                subscription_id += 1

        self.receiving_data = True
        self._set_timeout()

    async def _connect_websocket(self):
        """Establish WebSocket connection"""
        for endpoint in self.endpoints:
            try:
                self.websocket = await websockets.connect(  # type: ignore[awaitable-is-generator]
                    endpoint,
                    extra_headers={"Authorization": f"Bearer {self.token}"}
                )
                logger.info(f"Connected to Pyth Lazer WebSocket: {endpoint}")
                break
            except Exception as e:
                logger.warning(f"Failed to connect to {endpoint}: {e}")
                continue
        else:
            raise ConnectionError("Failed to connect to any Pyth Lazer endpoint")

    async def _subscribe_to_feeds(self, subscription_id: int, price_feed_array: PythLazerPriceFeedArray):
        """Subscribe to specific price feeds"""
        subscription_message = {
            "type": "subscribe",
            "subscriptionId": subscription_id,
            "priceFeedIds": price_feed_array.price_feed_ids,
            "properties": ["price", "bestAskPrice", "bestBidPrice", "exponent"],
            "formats": ["solana"],
            "deliveryFormat": "json",
            "channel": price_feed_array.channel.value if price_feed_array.channel else Channel.FIXED_RATE_200MS.value,
            "jsonBinaryEncoding": "hex"
        }

        if self.websocket:
            await self.websocket.send(json.dumps(subscription_message))

    async def _message_handler(self):
        """Handle incoming WebSocket messages"""
        if not self.websocket:
            logger.warning("No WebSocket connection available")
            return

        try:
            async for message in self.websocket:
                self.receiving_data = True
                if self.timeout_handle:
                    self.timeout_handle.cancel()

                await self._process_message(json.loads(message))
                self._set_timeout()

        except websockets.exceptions.ConnectionClosed:
            logger.warning("Pyth Lazer WebSocket connection closed")
            await self._handle_reconnection()

    async def _handle_reconnection(self):
        """Handle WebSocket reconnection"""
        if self.is_unsubscribing:
            return

        logger.info("Attempting to reconnect to Pyth Lazer WebSocket")
        await self.unsubscribe()
        self.receiving_data = False
        await self.subscribe()

    async def _process_message(self, message: Dict[str, Any]):
        """Process incoming price feed message"""
        if message.get("type") == "json":
            value = message.get("value", {})
            if value.get("type") == "streamUpdated":
                # Store Solana data
                if value.get("solana", {}).get("data"):
                    subscription_id = value.get("subscriptionId")
                    feed_ids_hash = self.subscription_ids_to_feed_ids_hash.get(subscription_id)
                    if feed_ids_hash:
                        self.feed_id_chunk_to_price_message[feed_ids_hash] = value["solana"]["data"]

                # Parse and store prices
                if value.get("parsed", {}).get("priceFeeds"):
                    for price_feed in value["parsed"]["priceFeeds"]:
                        try:
                            price = float(price_feed["price"]) * (10 ** float(price_feed["exponent"]))
                            feed_id = price_feed["priceFeedId"]
                            self.feed_id_to_price[feed_id] = price
                        except (KeyError, ValueError) as e:
                            logger.warning(f"Failed to parse price feed: {e}")

    def _set_timeout(self):
        """Set timeout for connection health monitoring"""
        if self.timeout_handle:
            self.timeout_handle.cancel()

        self.timeout_handle = asyncio.create_task(self._check_connection_timeout())

    async def _check_connection_timeout(self):
        """Check for connection timeout and resubscribe if needed"""
        await asyncio.sleep(self.resub_timeout_ms / 1000)

        if self.is_unsubscribing:
            return

        if self.receiving_data:
            logger.warning("No WebSocket data from Pyth Lazer client, resubscribing")
            await self.unsubscribe()
            self.receiving_data = False
            await self.subscribe()

    async def unsubscribe(self):
        """Unsubscribe and cleanup connections"""
        self.is_unsubscribing = True

        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        if self.timeout_handle:
            self.timeout_handle.cancel()
            self.timeout_handle = None

        self.is_unsubscribing = False

    def _hash_feed_ids(self, feed_ids: List[int]) -> str:
        """Create hash for feed ID array"""
        return f"h:{'|'.join(map(str, sorted(feed_ids)))}"

    async def get_latest_price_message(self, feed_ids: List[int]) -> Optional[str]:
        """Get latest price message for feed IDs"""
        if self.use_http_requests:
            return await self._get_price_message_via_http(feed_ids)

        feed_ids_hash = self._hash_feed_ids(feed_ids)
        return self.feed_id_chunk_to_price_message.get(feed_ids_hash)

    async def _get_price_message_via_http(self, feed_ids: List[int]) -> Optional[str]:
        """Get price message via HTTP request with Redis caching"""
        if len(feed_ids) == 1 and self.redis_client:
            # Try Redis cache first
            cache_key = f"pythLazerData:{feed_ids[0]}"
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    # cached_data is already the parsed data from DriftRedisClient
                    return cached_data
            except Exception as e:
                logger.warning(f"Redis cache error: {e}")

        # Fetch from HTTP endpoints
        for url in self.http_endpoints:
            price_message = await self._fetch_price_message_from_http(url, feed_ids)
            if price_message:
                # Cache in Redis if single feed
                if len(feed_ids) == 1 and self.redis_client:
                    try:
                        await self.redis_client.set(cache_key, price_message)
                    except Exception as e:
                        logger.warning(f"Redis cache write error: {e}")
                return price_message

        logger.warning("Pyth Lazer price undefined")
        return None

    async def _fetch_price_message_from_http(self, url: str, feed_ids: List[int]) -> Optional[str]:
        """Fetch price message from HTTP endpoint"""
        try:
            payload = {
                "priceFeedIds": feed_ids,
                "properties": ["price", "bestAskPrice", "bestBidPrice", "exponent"],
                "chains": ["solana"],
                "channel": "real_time",
                "jsonBinaryEncoding": "hex"
            }

            headers = {"Authorization": f"Bearer {self.token}"}

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("solana", {}).get("data")

        except Exception as e:
            logger.error(f"HTTP request failed for {url}: {e}")

        return None

    async def get_latest_price_message_for_market_index(self, market_index: int) -> Optional[str]:
        """Get price message for market index"""
        feed_ids = self.market_index_to_price_feed_id_chunk.get(market_index)
        if not feed_ids:
            return None
        return await self.get_latest_price_message(feed_ids)

    def get_price_feed_ids_from_market_index(self, market_index: int) -> List[int]:
        """Get feed IDs for market index"""
        return self.market_index_to_price_feed_id_chunk.get(market_index, [])

    def get_price_feed_ids_from_hash(self, hash_str: str) -> List[int]:
        """Get feed IDs from hash"""
        return self.feed_id_hash_to_feed_ids.get(hash_str, [])

    def get_price_from_market_index(self, market_index: int) -> Optional[float]:
        """Get current price for market index"""
        feed_id = self.market_index_to_price_feed_id.get(market_index)
        if feed_id is None:
            return None
        return self.feed_id_to_price.get(feed_id)

    async def start_message_handler(self):
        """Start the background message handler"""
        if self.websocket and not self.use_http_requests:
            asyncio.create_task(self._message_handler())

    async def health_check(self) -> bool:
        """Check if subscriber is healthy"""
        if self.use_http_requests:
            return len(self.http_endpoints) > 0

        return (
            self.websocket is not None and
            not self.websocket.closed and
            self.receiving_data
        )
