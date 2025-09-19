"""
Mock Driver Classes for JIT v3 Engine Integration
Provides compatibility with JIT v3 without disrupting existing client architecture
"""

import asyncio
import time
import random
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("libs.drift.mock_drivers")

class LocalAckDriver:
    """Local acknowledgment mock driver for development and testing"""
    
    def __init__(self, cfg: Dict[str, Any]):
        self.config = cfg
        self._last_hedge_ts = time.time()
        self._last_tick = {"price": 238.0, "ts": time.time()}
        
    async def get_mid_price(self) -> float:
        # Simulate price movement
        self._last_tick["price"] += (random.random() - 0.5) * 0.1
        self._last_tick["ts"] = time.time()
        return self._last_tick["price"]
    
    async def get_orderbook(self) -> Dict[str, Any]:
        mid = await self.get_mid_price()
        spread = 0.02  # $0.02 spread
        return {
            "bids": [[mid - spread/2, 100.0]],
            "asks": [[mid + spread/2, 100.0]],
            "best_bid": mid - spread/2,
            "best_ask": mid + spread/2
        }
    
    async def get_tick(self) -> Dict[str, Any]:
        await self.get_mid_price()  # Update price
        return {"price": self._last_tick["price"], "ts": self._last_tick["ts"]}
    
    async def get_realized_vol(self) -> float:
        return 0.02
    
    async def get_short_horizon_return(self) -> float:
        return (random.random() - 0.5) * 0.01
    
    async def get_atr(self) -> float:
        return 0.002
    
    async def get_pnl_step(self) -> float:
        return (random.random() - 0.5) * 0.0005
    
    async def get_portfolio_delta(self) -> float:
        return (random.random() - 0.5) * 200.0
    
    def time_since_last_hedge(self) -> float:
        return time.time() - self._last_hedge_ts
    
    async def quote_two_sided(self, ref_price: float, spread: float, size_mult: float, do_cr: bool, 
                             bid_size: Optional[float] = None, ask_size: Optional[float] = None):
        """Quote two-sided with optional bid/ask sizes (JIT v3 compatible)"""
        # In Local ACK mode, just sleep; sizes are accepted but unused
        _ = (bid_size, ask_size)
        await asyncio.sleep(0.005)
        logger.info(f"LocalACK Quote: ref=${ref_price:.4f}, spread=${spread:.4f}, "
                   f"mult={size_mult:.2f}, bid_size={bid_size}, ask_size={ask_size}")
    
    async def get_position(self) -> float:
        """Get current position (Local ACK returns 0 for neutrality)"""
        return 0.0
    
    async def should_refresh_quotes(self, ref_price: float, last_price: Optional[float], 
                                   move_bps: float, min_life_ms: int) -> bool:
        if last_price is None:
            return True
        move = abs(ref_price - last_price)
        bps = (move / max(1e-9, last_price)) * 10000.0
        return bps >= move_bps
    
    async def cancel_all(self):
        """Cancel all orders"""
        pass
    
    async def hedge(self, side: str, size: float, venue: str, order_type: str, 
                   slippage_bps: int, max_retries: int):
        """Execute hedge trade"""
        self._last_hedge_ts = time.time()
        await asyncio.sleep(0.002)
        logger.info(f"Hedge executed: {side} {size} via {venue}")
    
    async def trend_enter(self, side: str, size_mult: float):
        """Enter trend position"""
        await asyncio.sleep(0.002)
        logger.info(f"Trend enter: {side} with multiplier {size_mult}")
    
    async def trend_manage(self):
        """Manage trend position"""
        await asyncio.sleep(0.001)


class SwiftSidecarDriver(LocalAckDriver):
    """Swift sidecar driver with forwarding capability"""
    
    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(cfg)
        import os
        self.forward_base = cfg.get("swift", {}).get("forward_base") or os.getenv("SWIFT_FORWARD_BASE", "")
        self._use_forward = bool(self.forward_base)
        logger.info(f"SwiftSidecar initialized: forward_base={self.forward_base}, use_forward={self._use_forward}")
    
    async def quote_two_sided(self, ref_price: float, spread: float, size_mult: float, do_cr: bool,
                             bid_size: Optional[float] = None, ask_size: Optional[float] = None):
        """Quote via Swift sidecar or fallback to LocalACK"""
        if not self._use_forward:
            return await super().quote_two_sided(ref_price, spread, size_mult, do_cr, bid_size, ask_size)
        
        # TODO: Implement real HTTP calls to sidecar
        await asyncio.sleep(0.003)
        logger.info(f"Swift Quote: ref=${ref_price:.4f}, spread=${spread:.4f}, "
                   f"mult={size_mult:.2f}, bid_size={bid_size}, ask_size={ask_size}")
    
    async def cancel_all(self):
        """Cancel all orders via Swift or fallback"""
        if not self._use_forward:
            return await super().cancel_all()
        await asyncio.sleep(0.001)
        logger.info("Swift cancel_all executed")


async def build_mock_client_from_config(path: str):
    """Build a mock client for JIT v3 engine testing"""
    try:
        from libs.config.config_loader import load_yaml_with_env
        cfg = load_yaml_with_env(path)
    except ImportError:
        # Fallback if config loader not available
        import yaml
        with open(path, 'r') as f:
            cfg = yaml.safe_load(f)
    
    driver = cfg.get("driver", "swift")
    
    if driver == "swift":
        return SwiftSidecarDriver(cfg)
    else:
        return LocalAckDriver(cfg)


