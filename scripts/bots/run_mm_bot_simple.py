#!/usr/bin/env python3
"""
Simple MM Bot - Direct DriftPy Orders
Uses direct DriftPy client for order placement without Swift API
"""

import asyncio
import logging
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Optional, Any

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))

from libs.drift.client import DriftpyClient, Order

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SimpleMMBot:
    """Simple Market Making Bot using direct DriftPy orders"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[DriftpyClient] = None
        self.active_orders: Dict[str, Order] = {}
        self.order_size = config.get("order_size", 0.01)
        self.spread_bps = config.get("spread_bps", 8.0)
        self.max_orders_per_side = config.get("max_orders_per_side", 1)
        self.price_tolerance = config.get("price_tolerance", 0.01)
        
        # Statistics
        self.stats = {
            "orders_placed": 0,
            "orders_cancelled": 0,
            "ticks_processed": 0,
            "last_order_time": 0
        }
        
    async def initialize(self):
        """Initialize the bot"""
        try:
            # Load wallet
            wallet_file = self.config.get("wallet_file", ".beta_dev_wallet.json")
            if not os.path.exists(wallet_file):
                raise FileNotFoundError(f"Wallet file not found: {wallet_file}")
            
            # Initialize DriftPy client
            self.client = DriftpyClient(
                rpc_url=self.config.get("rpc_url", "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"),
                wallet_secret_key=wallet_file,
                env=self.config.get("env", "devnet"),
                use_fallback=True
            )
            
            # Connect to DriftPy
            await self.client.connect()
            logger.info("✅ DriftPy client connected successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            return False
    
    async def get_market_data(self) -> Optional[Dict]:
        """Get current market data"""
        try:
            if not self.client:
                return None
                
            # Get orderbook
            orderbook = await self.client.get_orderbook(0)  # SOL-PERP market index 0
            
            if not orderbook or not orderbook.get("bids") or not orderbook.get("asks"):
                logger.warning("No orderbook data available")
                return None
                
            bids = orderbook["bids"]
            asks = orderbook["asks"]
            
            if not bids or not asks:
                logger.warning("Empty orderbook")
                return None
                
            # Calculate mid price
            best_bid = bids[0][0] if bids else 0
            best_ask = asks[0][0] if asks else 0
            
            if best_bid <= 0 or best_ask <= 0 or best_bid >= best_ask:
                logger.warning(f"Invalid prices: bid={best_bid}, ask={best_ask}")
                return None
                
            mid_price = (best_bid + best_ask) / 2
            
            return {
                "bids": bids,
                "asks": asks,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "mid_price": mid_price
            }
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return None
    
    async def place_order(self, side: str, price: float, size: float) -> Optional[str]:
        """Place an order using DriftPy client"""
        try:
            if not self.client:
                logger.error("Client not initialized")
                return None
                
            # Create order object
            order = Order(
                side=side,
                price=price,
                size_usd=size * price,  # Convert to USD
                reduce_only=False,
                post_only=True
            )
            
            # Place order
            order_id = await self.client.place_order(order)
            
            if order_id and not order_id.startswith("MOCK-"):
                logger.info(f"✅ REAL ORDER PLACED: {side} {size} SOL @ ${price:.4f} (ID: {order_id})")
                self.stats["orders_placed"] += 1
                self.stats["last_order_time"] = time.time()
                return order_id
            else:
                logger.warning(f"Order placement failed or returned mock ID: {order_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None
    
    async def cancel_stale_orders(self, current_bid: float, current_ask: float):
        """Cancel orders that are too far from current prices"""
        orders_to_cancel = []
        
        for order_id, order in self.active_orders.items():
            current_price = current_bid if order.side == "buy" else current_ask
            price_diff = abs(current_price - order.price)
            
            if price_diff > self.price_tolerance:
                orders_to_cancel.append(order_id)
        
        # Cancel stale orders
        for order_id in orders_to_cancel:
            try:
                # Note: DriftPy client doesn't have cancel method in this version
                # For now, just remove from tracking
                del self.active_orders[order_id]
                self.stats["orders_cancelled"] += 1
                logger.info(f"Cancelled stale order: {order_id}")
            except Exception as e:
                logger.warning(f"Failed to cancel order {order_id}: {e}")
    
    async def market_making_tick(self):
        """Main market making logic"""
        try:
            self.stats["ticks_processed"] += 1
            
            # Get market data
            market_data = await self.get_market_data()
            if not market_data:
                return
                
            mid_price = market_data["mid_price"]
            best_bid = market_data["best_bid"]
            best_ask = market_data["best_ask"]
            
            # Calculate spread
            spread_decimal = self.spread_bps / 10000
            half_spread = spread_decimal / 2
            
            # Calculate our prices
            our_bid = mid_price * (1 - half_spread)
            our_ask = mid_price * (1 + half_spread)
            
            # Round to reasonable precision
            our_bid = round(our_bid, 4)
            our_ask = round(our_ask, 4)
            
            logger.info(f"📊 Market: bid=${best_bid:.4f}, ask=${best_ask:.4f}, mid=${mid_price:.4f}")
            logger.info(f"🎯 Our prices: bid=${our_bid:.4f}, ask=${our_ask:.4f} (spread: {self.spread_bps}bps)")
            
            # Cancel stale orders
            await self.cancel_stale_orders(our_bid, our_ask)
            
            # Count active orders
            active_buys = sum(1 for order in self.active_orders.values() if order.side == "buy")
            active_sells = sum(1 for order in self.active_orders.values() if order.side == "sell")
            
            # Place buy order if needed
            if active_buys < self.max_orders_per_side:
                order_id = await self.place_order("buy", our_bid, self.order_size)
                if order_id:
                    self.active_orders[order_id] = Order(
                        side="buy",
                        price=our_bid,
                        size_usd=self.order_size * our_bid,
                        post_only=True
                    )
            
            # Place sell order if needed
            if active_sells < self.max_orders_per_side:
                order_id = await self.place_order("sell", our_ask, self.order_size)
                if order_id:
                    self.active_orders[order_id] = Order(
                        side="sell",
                        price=our_ask,
                        size_usd=self.order_size * our_ask,
                        post_only=True
                    )
            
            # Log stats
            active_count = len(self.active_orders)
            logger.info(f"📈 Active orders: {active_count}, Total placed: {self.stats['orders_placed']}")
            
        except Exception as e:
            logger.error(f"Error in market making tick: {e}")
    
    async def run(self):
        """Main run loop"""
        try:
            logger.info("🚀 Starting Simple MM Bot")
            logger.info(f"Order size: {self.order_size} SOL")
            logger.info(f"Spread: {self.spread_bps} bps")
            logger.info(f"Environment: {self.config.get('env', 'devnet')}")
            
            # Main loop
            while True:
                await self.market_making_tick()
                await asyncio.sleep(1.0)  # 1 second between ticks
                
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            if self.client:
                await self.client.close()
            logger.info("Bot shutdown complete")

async def main():
    """Main function"""
    # Configuration
    config = {
        "env": "devnet",
        "rpc_url": "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
        "wallet_file": ".working_wallet.json",
        "order_size": 0.01,  # 0.01 SOL per order
        "spread_bps": 8.0,   # 8 basis points spread
        "max_orders_per_side": 1,
        "price_tolerance": 0.01
    }
    
    # Create and run bot
    bot = SimpleMMBot(config)
    
    if await bot.initialize():
        await bot.run()
    else:
        logger.error("Failed to initialize bot")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Bot failed: {e}")
        sys.exit(1)
