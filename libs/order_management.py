"""Order and position tracking helpers.

This module implements minimal classes to track positions and open
orders.  In a production trading system these classes would be
responsible for maintaining accurate state with respect to the
exchange, handling partial fills, and managing order identifiers.  The
implementations provided here are deliberately simple and intended
only as a starting point.

Key classes
-----------

``PositionTracker``
    Tracks the net long/short exposure (in quote currency) and the
    volume traded.  Exposures are updated whenever a fill is reported.

``OrderManager``
    Maintains a registry of open orders keyed by order ID.  Orders
    placed via the client should be recorded here so that they can be
    cancelled or reconciled later.  Order IDs are assumed to be
    returned by the client when placing orders.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class PositionTracker:
    """Tracks net exposure and volume.

    Attributes
    ----------
    net_exposure : float
        The net USD exposure of the position.  Positive values indicate a
        net long exposure (more buys than sells), negative values indicate
        net short exposure.
    volume : float
        Cumulative traded volume in USD.  This does not reset when
        positions are closed.
    """
    net_exposure: float = 0.0
    volume: float = 0.0

    def update(self, side: str, size_usd: float) -> None:
        """Update the exposure and volume based on a fill.

        Parameters
        ----------
        side : str
            ``"buy"`` for a long fill or ``"sell"`` for a short fill.
        size_usd : float
            The notional size of the fill in USD.
        """
        if side not in {"buy", "sell"}:
            logger.warning(f"Unknown side '{side}' for position update; ignoring")
            return
        delta = size_usd if side == "buy" else -size_usd
        self.net_exposure += delta
        self.volume += abs(size_usd)
        logger.debug(f"Updated position: exposure={self.net_exposure:.2f}, volume={self.volume:.2f}")

    def reset(self) -> None:
        """Reset exposure and volume to zero."""
        logger.info("Resetting position tracker")
        self.net_exposure = 0.0
        self.volume = 0.0


@dataclass
class OrderRecord:
    """Represents a single open order."""
    order_id: str
    side: str
    price: float
    size_usd: float


class OrderManager:
    """Simple manager for open orders.

    Orders are stored in a dictionary keyed by the exchange-assigned
    order ID.  This class supports adding, retrieving and cancelling
    orders.  In a real system the manager would listen for fill
    notifications and update the ``PositionTracker`` accordingly.
    """
    def __init__(self) -> None:
        self._orders: Dict[str, OrderRecord] = {}

    def add_order(self, order: OrderRecord) -> None:
        logger.info(f"Recording new order {order.order_id} {order.side} size={order.size_usd} price={order.price}")
        self._orders[order.order_id] = order

    def get_order(self, order_id: str) -> Optional[OrderRecord]:
        return self._orders.get(order_id)

    def cancel_order(self, order_id: str) -> None:
        if order_id in self._orders:
            logger.info(f"Cancelling tracked order {order_id}")
            del self._orders[order_id]

    def cancel_all(self) -> None:
        logger.info(f"Cancelling all {len(self._orders)} open orders")
        self._orders.clear()