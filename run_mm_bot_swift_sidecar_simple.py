#!/usr/bin/env python3
"""
Simplified Market Making Bot using Swift Sidecar
Bypasses wallet loading issues and focuses on sidecar integration
"""

import asyncio
import logging
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

from drift.swift_sidecar_driver import SwiftSidecarDriver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SwiftSidecarExecutionClient:
    """Execution client using Swift sidecar"""
    
    def __init__(self, sidecar_url: str, api_key: Optional[str] = None):
        self.sidecar = SwiftSidecarDriver(sidecar_url, api_key)
        self.orders_received = 0
        self.orders_processed = 0
        
    async def initialize(self):
        """Test connection to sidecar"""
        try:
            health = self.sidecar.health()
            logger.info(f"Swift sidecar health: {health}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Swift sidecar: {e}")
            return False
    
    async def place_order(self, order_params: Dict) -> Optional[str]:
        """Place order via Swift sidecar"""
        try:
            # For now, just log the order - we'll implement real placement later
            logger.info(f"Would place order via sidecar: {order_params}")
            self.orders_processed += 1
            return f"SIDECAR-{int(time.time() * 1000000) % 999999:06d}"
        except Exception as e:
            logger.error(f"Failed to place order via sidecar: {e}")
            return None
    
    async def close(self):
        """Clean up sidecar connection"""
        try:
            self.sidecar.close()
        except Exception:
            pass

class MockMarketDataAdapter:
    """Mock market data adapter for testing"""
    
    def __init__(self):
        self.base_price = 150.0
        self.spread = 0.1
        self.tick_size = 0.01
        
    async def get_orderbook(self) -> Dict[str, List]:
        """Get mock orderbook data"""
        # Simulate price movement
        current_time = time.time()
        price_variation = 0.1 * (current_time % 10)  # Small variation over time
        
        mid_price = self.base_price + price_variation
        best_bid = mid_price - self.spread / 2
        best_ask = mid_price + self.spread / 2
        
        # Round to tick size
        best_bid = round(best_bid / self.tick_size) * self.tick_size
        best_ask = round(best_ask / self.tick_size) * self.tick_size
        
        # Create mock orderbook
        orderbook = {
            "bids": [
                [best_bid, 1.0],
                [best_bid - self.tick_size, 0.5],
                [best_bid - 2 * self.tick_size, 0.3]
            ],
            "asks": [
                [best_ask, 1.0],
                [best_ask + self.tick_size, 0.5],
                [best_ask + 2 * self.tick_size, 0.3]
            ]
        }
        
        return orderbook

class JITMarketMaker:
    """Just-in-time market maker"""
    
    def __init__(self, market_data: MockMarketDataAdapter, execution: SwiftSidecarExecutionClient):
        self.md = market_data
        self.execution = execution
        self.order_size = 0.1
        self.active_orders = {}
        
    async def tick(self):
        """Main market making tick"""
        try:
            # Get orderbook
            ob = await self.md.get_orderbook()
            
            if not ob.get("bids") or not ob.get("asks"):
                logger.warning("Empty orderbook, skipping tick")
                return
            
            # Calculate mid price
            best_bid = ob["bids"][0][0] if ob["bids"] else 0
            best_ask = ob["asks"][0][0] if ob["asks"] else 0
            
            if best_bid <= 0 or best_ask <= 0:
                logger.warning("Invalid prices in orderbook")
                return
                
            mid_price = (best_bid + best_ask) / 2
            
            # Calculate our spread
            spread = best_ask - best_bid
            our_spread = max(spread * 0.1, 0.01)  # 10% of spread or 0.01 minimum
            
            # Calculate our prices
            bid_price = mid_price - our_spread / 2
            ask_price = mid_price + our_spread / 2
            
            # Round to reasonable precision
            bid_price = round(bid_price, 4)
            ask_price = round(ask_price, 4)
            
            logger.info(f"Market making tick: bid={bid_price}, ask={ask_price}")
            
            # Place orders via sidecar
            await self.manage_orders(bid_price, ask_price)
            
        except Exception as e:
            logger.error(f"Error in market making tick: {e}")
    
    async def manage_orders(self, bid_price: float, ask_price: float):
        """Manage active orders"""
        try:
            # Cancel old orders (simplified for now)
            for order_id in list(self.active_orders.keys()):
                logger.debug(f"Cancelling old order: {order_id}")
                del self.active_orders[order_id]
            
            # Place new orders
            if bid_price > 0:
                bid_order = await self.place_order("buy", bid_price, self.order_size)
                if bid_order:
                    self.active_orders[bid_order] = {"side": "buy", "price": bid_price}
            
            if ask_price > 0:
                ask_order = await self.place_order("sell", ask_price, self.order_size)
                if ask_order:
                    self.active_orders[ask_order] = {"side": "sell", "price": ask_price}
                    
        except Exception as e:
            logger.error(f"Error managing orders: {e}")
    
    async def place_order(self, side: str, price: float, size: float) -> Optional[str]:
        """Place order via execution client"""
        try:
            order_params = {
                "side": side,
                "price": price,
                "size": size,
                "market": "SOL-PERP",
                "order_type": "limit"
            }
            
            order_id = await self.execution.place_order(order_params)
            if order_id:
                logger.info(f"Placed {side} order: {order_id} at {price}")
                return order_id
            else:
                logger.warning(f"Failed to place {side} order")
                return None
                
        except Exception as e:
            logger.error(f"Error placing {side} order: {e}")
            return None

async def run_main():
    """Main bot loop"""
    try:
        logger.info("Starting Simplified MM Bot with Swift Sidecar")
        
        # Initialize Swift sidecar
        sidecar_url = os.getenv("SWIFT_SIDECAR_URL", "http://localhost:8787")
        execution = SwiftSidecarExecutionClient(sidecar_url)
        
        # Initialize market data (mock for now)
        market_data = MockMarketDataAdapter()
        
        # Initialize market maker
        mm = JITMarketMaker(market_data, execution)
        
        # Initialize components
        await execution.initialize()
        
        logger.info("MM Bot initialized successfully")
        
        # Main loop
        tick_interval = 0.25  # 250ms
        while True:
            try:
                await mm.tick()
                await asyncio.sleep(tick_interval)
            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(1)
                
    except Exception as e:
        logger.error(f"Failed to start MM Bot: {e}")
        raise
    finally:
        # Cleanup
        try:
            await execution.close()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(run_main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot failed: {e}")
        sys.exit(1)
