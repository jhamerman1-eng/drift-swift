"""
Robust Orderbook Normalizer for Drift Trading
Handles all orderbook formats from WebSocket, REST, sidecar proxy, and DriftPy models
"""

import time
from dataclasses import dataclass
from typing import Any, Iterable, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class CanonicalBook:
    """Canonical orderbook format with standardized bid/ask levels"""
    bids: List[Tuple[float, float]]  # [(price, size)] best->worst (highest price first)
    asks: List[Tuple[float, float]]  # [(price, size)] best->worst (lowest price first)
    source: str
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def is_valid(self) -> bool:
        """Check if orderbook has valid data and proper ordering"""
        if not self.bids or not self.asks:
            return False
        
        # Check if best bid < best ask (no crossing)
        if self.bids[0][0] >= self.asks[0][0]:
            return False
            
        # Check bid ordering (descending)
        for i in range(len(self.bids) - 1):
            if self.bids[i][0] < self.bids[i + 1][0]:
                return False
                
        # Check ask ordering (ascending)
        for i in range(len(self.asks) - 1):
            if self.asks[i][0] > self.asks[i + 1][0]:
                return False
                
        return True
    
    def get_spread(self) -> float:
        """Get bid-ask spread in price units"""
        if not self.bids or not self.asks:
            return float('inf')
        return self.asks[0][0] - self.bids[0][0]
    
    def get_mid_price(self) -> float:
        """Get mid price between best bid and ask"""
        if not self.bids or not self.asks:
            return 0.0
        return (self.bids[0][0] + self.asks[0][0]) / 2.0

def _pair(v: Any, pkey: str, skey: str) -> Tuple[float, float]:
    """Extract price/size pair from various formats"""
    # Accept [price, size] or (price, size)
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        return float(v[0]), float(v[1])
    
    # Accept dict with various key names
    if isinstance(v, dict):
        if pkey in v and skey in v:
            return float(v[pkey]), float(v[skey])
        
        # Common alternates
        alternates = [
            ("px", "sz"),
            ("price", "quantity"),
            ("p", "q"),
            ("price", "amount"),
            ("px", "qty")
        ]
        
        for pk, sk in alternates:
            if pk in v and sk in v:
                return float(v[pk]), float(v[sk])
    
    raise TypeError(f"unsupported orderbook level shape: {type(v)} {v}")

def normalize_orderbook(raw: Any) -> CanonicalBook:
    """
    Accepts any orderbook format and returns CanonicalBook:
      - {'bids': [...], 'asks': [...]} (standard format)
      - [{'price':..,'size':..}, ...] (single side or list format)
      - {'data': {'bids': [...], 'asks': [...]}} (wrapped format)
      - {'orderbook': {'bids': [...], 'asks': [...]}} (nested format)
      - DriftPy/Anchor objects with .bids/.asks attributes
      - Sidecar proxy responses with [px,sz] arrays
      - Swift API responses
    """
    src = type(raw).__name__
    original_raw = raw

    try:
        # Unwrap common envelopes
        if isinstance(raw, dict):
            for key in ("orderbook", "data", "result", "book"):
                if key in raw and isinstance(raw[key], (dict, list)):
                    raw = raw[key]
                    src += f".{key}"
                    break

        # Handle dict-based books (most common)
        if isinstance(raw, dict):
            bids = raw.get("bids")
            asks = raw.get("asks")
            
            if bids is not None and asks is not None:
                def norm_side(side):
                    if not side:
                        return []
                    
                    out = []
                    for lvl in side:
                        try:
                            out.append(_pair(lvl, "price", "size"))
                        except TypeError:
                            try:
                                out.append(_pair(lvl, "p", "q"))
                            except TypeError:
                                # Skip malformed levels
                                logger.debug(f"Skipping malformed level: {lvl}")
                                continue
                    return out
                
                bids_norm = norm_side(bids)
                asks_norm = norm_side(asks)
                
                # Sort to ensure proper ordering
                bids_norm.sort(key=lambda x: x[0], reverse=True)  # Descending price
                asks_norm.sort(key=lambda x: x[0])               # Ascending price
                
                return CanonicalBook(bids=bids_norm, asks=asks_norm, source=src)

        # Handle objects with .bids/.asks attributes (DriftPy)
        if hasattr(raw, "bids") and hasattr(raw, "asks"):
            def attr_iter(x):
                if x is None:
                    return []
                # Handle various iterables
                try:
                    return list(x) if isinstance(x, Iterable) else []
                except TypeError:
                    return []
            
            bids = [_pair(l, "price", "size") for l in attr_iter(raw.bids)]
            asks = [_pair(l, "price", "size") for l in attr_iter(raw.asks)]
            
            # Sort to ensure proper ordering
            bids.sort(key=lambda x: x[0], reverse=True)
            asks.sort(key=lambda x: x[0])
            
            return CanonicalBook(bids=bids, asks=asks, source=src)

        # Handle list formats
        if isinstance(raw, list):
            # Check for [{'bids':..,'asks':..}] format
            if raw and isinstance(raw[0], dict) and "bids" in raw[0] and "asks" in raw[0]:
                return normalize_orderbook(raw[0])
            
            # Check for [bids_list, asks_list] format
            if len(raw) == 2 and all(isinstance(x, list) for x in raw):
                bids = [_pair(l, "price", "size") for l in raw[0]]
                asks = [_pair(l, "price", "size") for l in raw[1]]
                
                bids.sort(key=lambda x: x[0], reverse=True)
                asks.sort(key=lambda x: x[0])
                
                return CanonicalBook(bids=bids, asks=asks, source=src)
            
            # Single side list (assume bids)
            if raw:
                bids = [_pair(l, "price", "size") for l in raw]
                bids.sort(key=lambda x: x[0], reverse=True)
                return CanonicalBook(bids=bids, asks=[], source=src + ".bids_only")

        raise TypeError(f"unrecognized orderbook shape: {src}")

    except Exception as e:
        logger.error(f"Failed to normalize orderbook from {src}: {e}")
        logger.debug(f"Raw data: {original_raw}")
        raise TypeError(f"orderbook normalization failed: {src} - {e}")

# Global state for orderbook management
last_book: Optional[CanonicalBook] = None
last_ok_ts: float = 0
log_throttle = {}

def should_log_now(key: str, period: float = 10.0) -> bool:
    """Throttle logging to avoid spam"""
    now = time.time()
    if key not in log_throttle or (now - log_throttle[key]) >= period:
        log_throttle[key] = now
        return True
    return False

def handle_orderbook_message(msg: Any) -> bool:
    """Handle incoming orderbook message and update global state"""
    global last_book, last_ok_ts
    
    try:
        book = normalize_orderbook(msg)
        
        # Validate the book
        if not book.is_valid():
            if should_log_now("invalid_book", period=5):
                logger.warning(f"Invalid orderbook received: spread={book.get_spread():.4f}")
            return False
        
        last_book = book
        last_ok_ts = time.time()
        
        logger.debug(f"Orderbook updated: {len(book.bids)} bids, {len(book.asks)} asks, "
                    f"spread={book.get_spread():.4f}, mid=${book.get_mid_price():.4f}")
        return True
        
    except Exception as e:
        if should_log_now("ob_parse_err", period=10):
            logger.error(f"Failed to parse orderbook: {e}")
        return False

# Configuration
STALE_BOOK_SECS = 3.0

def orderbook_ready() -> bool:
    """Check if we have a fresh, valid orderbook"""
    return (last_book is not None 
            and last_book.is_valid() 
            and (time.time() - last_ok_ts) <= STALE_BOOK_SECS)

def get_current_book() -> Optional[CanonicalBook]:
    """Get current orderbook if ready"""
    return last_book if orderbook_ready() else None

def get_microprice(alpha: float = 0.5) -> Optional[float]:
    """Calculate microprice from current orderbook"""
    if not orderbook_ready():
        return None
    
    book = last_book
    if not book.bids or not book.asks:
        return None
    
    best_bid, bid_size = book.bids[0]
    best_ask, ask_size = book.asks[0]
    
    # Volume-weighted microprice
    total_size = bid_size + ask_size
    if total_size == 0:
        return (best_bid + best_ask) / 2.0
    
    return (best_bid * ask_size + best_ask * bid_size) / total_size
