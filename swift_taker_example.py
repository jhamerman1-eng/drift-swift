import asyncio
import logging
import random
import time
from typing import Optional, Dict, Any
from decimal import Decimal, ROUND_DOWN
import base64
import hashlib
from urllib.parse import quote

from driftpy.drift_client import DriftClient
from driftpy.types import MarketType, PositionDirection, OrderParams
from driftpy.constants import QUOTE_PRECISION, BASE_PRECISION, PRICE_PRECISION
from driftpy.math import floor_to_nearest

logger = logging.getLogger(__name__)

CONFIRM_TIMEOUT = 30_000  # 30 seconds

class SwiftTaker:
    """
    Swift market taker that places random orders through the Swift API.
    """

    def __init__(
        self,
        drift_client: DriftClient,
        drift_env: str,
        interval_ms: int = 60000  # 1 minute default
    ):
        """
        Initialize the Swift taker.

        Args:
            drift_client: Initialized Drift client
            drift_env: Environment ('mainnet-beta' or 'devnet')
            interval_ms: Interval between order placements in milliseconds
        """
        self.drift_client = drift_client
        self.interval_ms = interval_ms
        self.swift_url = (
            'https://swift.drift.trade'
            if drift_env == 'mainnet-beta'
            else 'https://master.swift.drift.trade'
        )
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def init(self) -> None:
        """Initialize and start the taker."""
        await self.start_interval()

    async def health_check(self) -> bool:
        """Health check method."""
        return True

    async def start_interval(self) -> None:
        """Start the periodic order placement loop."""
        if self._running:
            return

        self._running = True
        market_indexes = [0, 1, 2]  # Markets to trade

        async def order_loop():
            while self._running:
                try:
                    # Random delay for different metrics timing
                    await asyncio.sleep(random.random() * 5)

                    # Get current slot
                    slot = await self.drift_client.connection.get_slot()

                    # Random direction
                    direction = (
                        PositionDirection.Long
                        if random.random() > 0.5
                        else PositionDirection.Short
                    )

                    # Random market selection
                    market_index = random.choice(market_indexes)

                    # Get oracle data
                    oracle_info = self.drift_client.get_oracle_data_for_perp_market(market_index)
                    eps_bps = 100  # 1%

                    # Calculate price bounds
                    high_price = self._plus_bps(oracle_info.price, eps_bps)
                    low_price = self._minus_bps(oracle_info.price, eps_bps)

                    # Sample trade size
                    trade_size_dollars = self._sample_trade_size_dollars()
                    trade_size = self._calculate_trade_size(
                        trade_size_dollars, oracle_info.price
                    )

                    # Get perp market account
                    perp_market_account = self.drift_client.get_perp_market_account(market_index)
                    if not perp_market_account:
                        logger.error(f"Perp market {market_index} not found")
                        continue

                    # Floor to nearest order step size
                    base_asset_amount = floor_to_nearest(
                        trade_size,
                        perp_market_account.amm.order_step_size
                    )

                    # Create market order params
                    market_order_params = {
                        'market_index': market_index,
                        'market_type': MarketType.Perp,
                        'direction': direction,
                        'base_asset_amount': base_asset_amount,
                        'auction_start_price': low_price if direction == PositionDirection.Long else high_price,
                        'auction_end_price': high_price if direction == PositionDirection.Long else low_price,
                        'auction_duration': 50,
                    }

                    # Create order message
                    order_message = {
                        'signed_msg_order_params': market_order_params,
                        'sub_account_id': self.drift_client.active_sub_account_id,
                        'slot': slot,
                        'uuid': self._generate_uuid(),
                        'stop_loss_order_params': None,
                        'take_profit_order_params': None,
                    }

                    # Sign the order
                    signed_order = await self.drift_client.sign_signed_msg_order_params_message(
                        order_message
                    )

                    # Calculate hash for tracking
                    signature_bytes = bytes.fromhex(signed_order.signature[2:] if signed_order.signature.startswith('0x') else signed_order.signature)
                    order_hash = hashlib.sha256(signature_bytes).hexdigest()

                    logger.info(
                        f"Sending order in slot: {slot}, time: {int(time.time() * 1000)}, hash: {order_hash}"
                    )

                    # Submit order to Swift API
                    success = await self._submit_order_to_swift(
                        market_index,
                        signed_order.order_params,
                        signed_order.signature,
                        order_hash
                    )

                    if success:
                        # Wait for confirmation
                        await self._wait_for_confirmation(order_hash)

                except Exception as e:
                    logger.error(f"Error in order loop: {e}")
                    await asyncio.sleep(5)  # Brief pause on error

                # Wait for next interval
                await asyncio.sleep(self.interval_ms / 1000)

        self._task = asyncio.create_task(order_loop())

    async def stop(self) -> None:
        """Stop the taker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def _plus_bps(self, price: int, bps: int) -> int:
        """Add basis points to price."""
        return (price * (10000 + bps)) // 10000

    def _minus_bps(self, price: int, bps: int) -> int:
        """Subtract basis points from price."""
        return (price * (10000 - bps)) // 10000

    def _sample_trade_size_dollars(self) -> float:
        """
        Sample trade size with distribution:
        - 60% small trades: $100 - $5,000
        - 25% medium trades: $5,000 - $20,000
        - 15% large trades: $20,000 - $70,000
        """
        rand = random.random()

        if rand < 0.6:
            # 60% small trades: $100 - $5,000
            return 100 + random.random() * 4900
        elif rand < 0.85:
            # 25% medium trades: $5,000 - $20,000
            return 5000 + random.random() * 15000
        else:
            # 15% large trades: $20,000 - $70,000
            return 20000 + random.random() * 50000

    def _calculate_trade_size(self, trade_size_dollars: float, price: int) -> int:
        """Calculate base asset amount from dollar value."""
        return int(
            Decimal(str(trade_size_dollars))
            * Decimal(str(QUOTE_PRECISION))
            * Decimal(str(PRICE_PRECISION))
            * Decimal(str(BASE_PRECISION // PRICE_PRECISION))
            / Decimal(str(price))
        )

    def _generate_uuid(self) -> str:
        """Generate a UUID for the order."""
        import uuid
        return str(uuid.uuid4())

    async def _submit_order_to_swift(
        self,
        market_index: int,
        order_params: Any,
        signature: str,
        order_hash: str
    ) -> bool:
        """Submit order to Swift API."""
        try:
            import aiohttp

            order_data = {
                'market_index': market_index,
                'market_type': 'perp',
                'message': str(order_params),
                'signature': signature,
                'taker_pubkey': str(self.drift_client.wallet.public_key),
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.swift_url}/orders",
                    json=order_data,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error(f"Failed to send order: {await response.text()}")
                        return False

        except ImportError:
            logger.error("aiohttp not available, install with: pip install aiohttp")
            return False
        except Exception as e:
            logger.error(f"Error submitting order to Swift: {e}")
            return False

    async def _wait_for_confirmation(self, order_hash: str) -> None:
        """Wait for order confirmation from Swift."""
        try:
            import aiohttp

            expire_time = time.time() * 1000 + CONFIRM_TIMEOUT

            async with aiohttp.ClientSession() as session:
                while time.time() * 1000 < expire_time:
                    try:
                        async with session.get(
                            f"{self.swift_url}/confirmation/hash-status?hash={quote(order_hash)}"
                        ) as response:
                            if response.status == 200:
                                logger.info(f"Confirmed order hash: {order_hash}")
                                return
                            elif response.status >= 500:
                                logger.error(f"Server error confirming hash: {order_hash}")
                                break

                        await asyncio.sleep(10)  # Wait 10 seconds before retry

                    except Exception as e:
                        logger.error(f"Error checking confirmation: {e}")
                        await asyncio.sleep(10)

            logger.error(f"Failed to confirm order hash: {order_hash}")

        except ImportError:
            logger.error("aiohttp not available for confirmation checking")


# Example usage
async def example_usage():
    """
    Example of how to use the SwiftTaker.
    """
    # Note: This would need actual DriftClient initialization
    # drift_client = DriftClient(...)
    # taker = SwiftTaker(drift_client, "devnet", 60000)
    # await taker.init()
    # await asyncio.sleep(300)  # Run for 5 minutes
    # await taker.stop()

    print("SwiftTaker example - would need actual DriftClient setup")


if __name__ == "__main__":
    asyncio.run(example_usage())

