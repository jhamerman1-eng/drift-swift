# libs/market/__init__.py
"""
Market data utilities and safe wrappers for orderbook handling.

This module provides defensive programming patterns to prevent
common async/sync misuse errors in trading applications.
"""

from .orderbook_snapshot import (
    OrderbookSnapshot,
    SafeAwaitError,
    snapshot_from_driver_ob,
    snapshot_from_raw_data
)

__all__ = [
    'OrderbookSnapshot',
    'SafeAwaitError',
    'snapshot_from_driver_ob',
    'snapshot_from_raw_data'
]
