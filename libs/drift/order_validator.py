#!/usr/bin/env python3
"""
Order Validator with Pyth Price Integration

Validates Swift orders against real-time Pyth price feeds to ensure:
- Orders are placed within reasonable price bounds
- Auction parameters are realistic
- Price manipulation detection
"""

import logging
from typing import Dict, Any, Optional, Tuple

from ..pyth.pyth_lazer_subscriber import PythLazerSubscriber

logger = logging.getLogger(__name__)

class OrderValidator:
    """
    Validates orders using Pyth price feeds for price accuracy and market sanity checks
    """

    def __init__(self, pyth_subscriber: Optional[PythLazerSubscriber] = None):
        self.pyth_subscriber = pyth_subscriber

    async def validate_order_price(self, order: Dict[str, Any]) -> Tuple[bool, str, Optional[float]]:
        """
        Validate order price against Pyth feeds

        Args:
            order: Order parameters with market_index, price, etc.

        Returns:
            Tuple of (is_valid, reason, pyth_price)
        """
        if not self.pyth_subscriber:
            return True, "No Pyth subscriber available", None

        market_index = order.get("market_index")
        if market_index is None:
            return False, "Missing market_index", None

        try:
            # Get Pyth price for this market
            pyth_price = self.pyth_subscriber.get_price_from_market_index(market_index)

            if pyth_price is None:
                return False, f"No Pyth price available for market {market_index}", None

            order_price = order.get("price") or order.get("auction_start_price")
            if order_price is None:
                return False, "Order missing price information", pyth_price

            # Convert to comparable units (assuming PRICE_PRECISION = 1e6)
            order_price_usd = order_price / 1_000_000
            price_diff_pct = abs(order_price_usd - pyth_price) / pyth_price * 100

            # Allow up to 5% price deviation for market orders (allows for slippage)
            max_deviation = 5.0
            if order.get("order_type") == "limit":
                max_deviation = 2.0  # Stricter for limit orders

            if price_diff_pct > max_deviation:
                return False, f"Price deviation too high: {price_diff_pct:.2f}% (max: {max_deviation}%)", pyth_price

            return True, f"Price validated (deviation: {price_diff_pct:.2f}%)", pyth_price

        except Exception as e:
            logger.error(f"Price validation error for market {market_index}: {e}")
            return False, f"Price validation failed: {str(e)}", None

    async def validate_auction_params(self, order: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate auction parameters against Pyth prices

        Args:
            order: Order with auction parameters

        Returns:
            Tuple of (is_valid, reason)
        """
        if not self.pyth_subscriber:
            return True, "No Pyth subscriber available"

        market_index = order.get("market_index")
        if market_index is None:
            return False, "Missing market_index"

        try:
            pyth_price = self.pyth_subscriber.get_price_from_market_index(market_index)
            if pyth_price is None:
                return False, f"No Pyth price available for market {market_index}"

            auction_start = order.get("auction_start_price")
            auction_end = order.get("auction_end_price")

            if auction_start is None or auction_end is None:
                return False, "Missing auction price parameters"

            # Convert to USD
            start_usd = auction_start / 1_000_000
            end_usd = auction_end / 1_000_000

            # Validate auction range is reasonable (within 10% of Pyth price)
            max_range = pyth_price * 0.10  # 10% range allowed
            auction_range = abs(end_usd - start_usd)

            if auction_range > max_range:
                return False, f"Auction range too wide: ${auction_range:.2f} (max: ${max_range:.2f})"

            # Validate direction makes sense
            direction = order.get("direction", "").lower()
            if direction == "long" and start_usd > end_usd:
                return False, "Long order auction should start low and end high"
            elif direction == "short" and start_usd < end_usd:
                return False, "Short order auction should start high and end low"

            return True, "Auction parameters validated"

        except Exception as e:
            logger.error(f"Auction validation error for market {market_index}: {e}")
            return False, f"Auction validation failed: {str(e)}"

    async def validate_swift_order(self, order: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Comprehensive validation for Swift orders

        Args:
            order: Complete Swift order parameters

        Returns:
            Tuple of (is_valid, reason)
        """
        # Validate basic price
        price_valid, price_reason, pyth_price = await self.validate_order_price(order)
        if not price_valid:
            return False, f"Price validation failed: {price_reason}"

        # Validate auction parameters if present
        if "auction_start_price" in order and "auction_end_price" in order:
            auction_valid, auction_reason = await self.validate_auction_params(order)
            if not auction_valid:
                return False, f"Auction validation failed: {auction_reason}"

        # Additional validations can be added here

        return True, f"Order validated successfully (Pyth price: ${pyth_price:.2f})"

    def set_pyth_subscriber(self, subscriber: PythLazerSubscriber):
        """Update the Pyth subscriber reference"""
        self.pyth_subscriber = subscriber

