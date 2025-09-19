from typing import Dict, Optional, List, Callable, Any
from pythclient.pythclient import PythClient
from pythclient.pythaccounts import PythPriceAccount
import asyncio
import logging

logger = logging.getLogger(__name__)

class PythPriceFeedSubscriber:
    """
    Pyth price feed subscriber that caches VAAs (Verified Asset Attestations)
    for efficient retrieval in trading applications.
    """

    def __init__(self, endpoint: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Pyth price feed subscriber.

        Args:
            endpoint: Pyth service endpoint URL
            config: Optional configuration dictionary
        """
        self.endpoint = endpoint
        self.config = config or {}
        self.latest_pyth_vaas: Dict[str, str] = {}  # price_feed_id -> vaa
        self.client: Optional[PythClient] = None
        self.subscribed_feeds: set = set()
        self._running = False

    async def connect(self) -> None:
        """
        Establish connection to Pyth service.
        """
        try:
            self.client = PythClient(endpoint=self.endpoint)
            logger.info(f"Connected to Pyth service at {self.endpoint}")
        except Exception as e:
            logger.error(f"Failed to connect to Pyth service: {e}")
            raise

    async def subscribe(self, feed_ids: List[str]) -> None:
        """
        Subscribe to price feed updates for the given feed IDs.

        Args:
            feed_ids: List of price feed IDs to subscribe to
        """
        if not self.client:
            await self.connect()

        for feed_id in feed_ids:
            if feed_id not in self.subscribed_feeds:
                self.subscribed_feeds.add(feed_id)
                logger.info(f"Subscribed to price feed: {feed_id}")

        # Start the update loop if not already running
        if not self._running:
            self._running = True
            asyncio.create_task(self._update_loop())

    async def _update_loop(self) -> None:
        """
        Background loop to fetch price updates and cache VAAs.
        """
        while self._running:
            try:
                if self.client and self.subscribed_feeds:
                    # Get price accounts for subscribed feeds
                    for feed_id in self.subscribed_feeds:
                        try:
                            price_account = self.client.get_price_account(feed_id)
                            if price_account and price_account.vaa:
                                # Cache the VAA with '0x' prefix for consistency
                                price_feed_id = f"0x{feed_id}"
                                self.latest_pyth_vaas[price_feed_id] = price_account.vaa
                        except Exception as e:
                            logger.warning(f"Failed to get price for feed {feed_id}: {e}")

                await asyncio.sleep(1)  # Update every second

            except Exception as e:
                logger.error(f"Error in price update loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    def get_latest_cached_vaa(self, feed_id: str) -> Optional[str]:
        """
        Get the latest cached VAA for a given feed ID.

        Args:
            feed_id: Price feed ID (with or without '0x' prefix)

        Returns:
            The cached VAA string or None if not available
        """
        # Ensure feed_id has '0x' prefix for consistency
        if not feed_id.startswith('0x'):
            feed_id = f"0x{feed_id}"

        return self.latest_pyth_vaas.get(feed_id)

    def get_all_cached_vaas(self) -> Dict[str, str]:
        """
        Get all cached VAAs.

        Returns:
            Dictionary of feed_id -> vaa mappings
        """
        return self.latest_pyth_vaas.copy()

    def is_subscribed(self, feed_id: str) -> bool:
        """
        Check if a feed ID is currently subscribed.

        Args:
            feed_id: Price feed ID to check

        Returns:
            True if subscribed, False otherwise
        """
        return feed_id in self.subscribed_feeds

    async def unsubscribe(self, feed_ids: List[str]) -> None:
        """
        Unsubscribe from price feeds.

        Args:
            feed_ids: List of feed IDs to unsubscribe from
        """
        for feed_id in feed_ids:
            if feed_id in self.subscribed_feeds:
                self.subscribed_feeds.remove(feed_id)
                logger.info(f"Unsubscribed from price feed: {feed_id}")

    async def stop(self) -> None:
        """
        Stop the subscriber and clean up resources.
        """
        self._running = False
        self.subscribed_feeds.clear()
        self.latest_pyth_vaas.clear()

        if self.client:
            # Close connection if the client supports it
            try:
                await self.client.close()
            except:
                pass
            self.client = None

        logger.info("Pyth price feed subscriber stopped")


# Example usage
async def example_usage():
    """
    Example of how to use the PythPriceFeedSubscriber.
    """
    # Initialize subscriber
    subscriber = PythPriceFeedSubscriber(
        endpoint="https://xc-mainnet.pyth.network",
        config={"timeout": 30}
    )

    # Subscribe to some price feeds
    feed_ids = [
        "0xef0d8b6fda2ceba41da15d4095d1da392a0d2f8ed0c6c7bc0f4cfac8c280b56d",  # BTC/USD
        "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace",   # ETH/USD
    ]

    await subscriber.subscribe(feed_ids)

    # Wait a bit for updates
    await asyncio.sleep(5)

    # Get cached VAAs
    btc_vaa = subscriber.get_latest_cached_vaa("0xef0d8b6fda2ceba41da15d4095d1da392a0d2f8ed0c6c7bc0f4cfac8c280b56d")
    eth_vaa = subscriber.get_latest_cached_vaa("0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace")

    print(f"BTC VAA: {btc_vaa}")
    print(f"ETH VAA: {eth_vaa}")

    # Clean up
    await subscriber.stop()


if __name__ == "__main__":
    asyncio.run(example_usage())

