#!/usr/bin/env python3
"""
Complete Swift Market Making Bot - FIXED VERSION
Integrates real order placement, Swift order reception, and proper order management
"""

import asyncio
import logging
import os
import sys
import time
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

from drift.swift_sidecar_driver import SwiftSidecarDriver
from driftpy.drift_client import DriftClient
from drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
from drift.swift_receiver import SwiftOrderReceiver, SwiftOrderProcessor, SwiftOrderMessage
from solders.keypair import Keypair

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@dataclass
class OrderInfo:
    """Information about an active order"""
    order_id: str
    side: str
    price: float
    size: float
    timestamp: float
    status: str = "active"

class CompleteSwiftMMBot:
    """Complete Swift Market Making Bot with all features"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.drift_client = None
        self.keypair = None
        
        # Initialize components
        self.sidecar_client = SwiftSidecarDriver(
            config.get("sidecar_url", "http://localhost:8787"),
            config.get("sidecar_api_key")
        )
        self.envelope_creator = SwiftEnvelopeCreator()
        self.swift_receiver = SwiftOrderReceiver(
            config.get("swift_websocket_url", "wss://swift.drift.trade/ws"),
            config.get("swift_api_key")
        )
        self.swift_processor = None
        
        # Market making state
        self.active_orders: Dict[str, OrderInfo] = {}
        self.order_size = config.get("order_size", 0.01)
        self.max_orders_per_side = config.get("max_orders_per_side", 1)
        self.price_tolerance = config.get("price_tolerance", 0.01)
        self.spread_bps = config.get("spread_bps", 8)
        
        # Statistics
        self.stats = {
            "orders_placed": 0,
            "orders_cancelled": 0,
            "swift_orders_received": 0,
            "swift_orders_processed": 0,
            "jit_trades_executed": 0
        }
        
    async def initialize(self):
        """Initialize all components"""
        try:
            # Load wallet
            await self._load_wallet()
            
            # Initialize DriftPy client
            await self._initialize_drift_client()
            
            # Initialize Swift processor
            self.swift_processor = SwiftOrderProcessor(self.drift_client, self.keypair)
            
            # Test sidecar connection
            health = self.sidecar_client.health()
            logger.info(f"Swift sidecar health: {health}")
            
            logger.info("Complete Swift MM Bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            return False
    
    async def _load_wallet(self):
        """Load wallet from file"""
        wallet_file = self.config.get("wallet_file", ".valid_wallet.json")
        
        if not os.path.exists(wallet_file):
            raise FileNotFoundError(f"Wallet file not found: {wallet_file}")
        
        with open(wallet_file, 'r') as f:
            wallet_data = json.load(f)
        
        # Create keypair from wallet data
        if isinstance(wallet_data, list):
            secret_key = bytes(wallet_data)
        else:
            secret_key = bytes(wallet_data["secret_key"])
        
        self.keypair = Keypair.from_bytes(secret_key)
        logger.info(f"Wallet loaded: {self.keypair.pubkey()}")
    
    async def _initialize_drift_client(self):
        """Initialize DriftPy client"""
        env = self.config.get("env", "devnet")
        rpc_url = self.config.get("rpc_url", "https://api.devnet.solana.com")
        
        # Normalize environment
        env_norm = env.lower()
        if env_norm in ("beta", "mainnet-beta"):
            env_norm = "devnet" if env_norm == "beta" else "mainnet"
        
        from solana.rpc.async_api import AsyncClient
        
        self.drift_client = DriftClient(
            connection=AsyncClient(rpc_url),
            wallet=self.keypair,
            env=env_norm
        )
        
        # Add user then subscribe (recommended order)
        await self.drift_client.add_user(0)
        await self.drift_client.subscribe()
        
        logger.info(f"DriftPy client connected to {env_norm}")
    
    async def start_swift_receiver(self):
        """Start receiving Swift orders with error handling"""
        try:
            await self.swift_receiver.start(self._handle_swift_order)
            logger.info("Swift order receiver started")
            return True
        except Exception as e:
            logger.warning(f"Failed to start Swift receiver: {e}")
            logger.info("Continuing without Swift order reception...")
            return False
    
    async def _handle_swift_order(self, order: SwiftOrderMessage):
        """Handle incoming Swift order"""
        try:
            self.stats["swift_orders_received"] += 1
            logger.info(f"Swift order received: {order.side} {order.size} @ {order.price}")
            
            # Process the order
            result = await self.swift_processor.process_order(order)
            
            if result["status"] == "success":
                self.stats["swift_orders_processed"] += 1
                self.stats["jit_trades_executed"] += 1
                logger.info(f"JIT trade executed: {result['message']}")
            else:
                logger.warning(f"Swift order rejected: {result.get('reason', 'Unknown')}")
                
        except Exception as e:
            logger.error(f"Error handling Swift order: {e}")

    async def market_making_tick(self):
        """Main market making tick"""
        try:
            # Get orderbook
            ob = await self._get_orderbook()
            if not ob:
                return
            
            # Calculate prices
            bid_price, ask_price = self._calculate_prices(ob)
            if not bid_price or not ask_price:
                return
            
            # Manage orders
            await self._manage_orders(bid_price, ask_price)
            
        except Exception as e:
            logger.error(f"Error in market making tick: {e}")
    
    async def _get_orderbook(self) -> Optional[Dict]:
        """Get orderbook data"""
        try:
            ob = await self.drift_client.get_l2_orderbook_compat("SOL-PERP", 10)
            if ob and ob.get("bids") and ob.get("asks"):
                return ob
            return None
        except Exception as e:
            logger.debug(f"Failed to get orderbook: {e}")
            return None
    
    def _calculate_prices(self, ob: Dict) -> Tuple[Optional[float], Optional[float]]:
        """Calculate bid and ask prices"""
        try:
            best_bid = ob["bids"][0][0] if ob["bids"] else 0
            best_ask = ob["asks"][0][0] if ob["asks"] else 0
            
            if best_bid <= 0 or best_ask <= 0:
                return None, None
            
            mid_price = (best_bid + best_ask) / 2
            spread = mid_price * (self.spread_bps / 10000)  # Convert bps to decimal
            
            bid_price = round(mid_price - spread / 2, 4)
            ask_price = round(mid_price + spread / 2, 4)
            
            return bid_price, ask_price
            
        except Exception as e:
            logger.error(f"Error calculating prices: {e}")
            return None, None
    
    async def _manage_orders(self, bid_price: float, ask_price: float):
        """Manage active orders"""
        try:
            # Cancel stale orders
            await self._cancel_stale_orders(bid_price, ask_price)
            
            # Place new orders
            await self._place_new_orders(bid_price, ask_price)
            
        except Exception as e:
            logger.error(f"Error managing orders: {e}")
    
    async def _cancel_stale_orders(self, bid_price: float, ask_price: float):
        """Cancel orders that are too far from current prices"""
        orders_to_cancel = []
        
        for order_id, order_info in self.active_orders.items():
            if order_info.status != "active":
                continue
            
            current_price = bid_price if order_info.side == "buy" else ask_price
            price_diff = abs(current_price - order_info.price)
            age_seconds = time.time() - order_info.timestamp
            
            if price_diff > self.price_tolerance or age_seconds > 30:
                orders_to_cancel.append(order_id)
        
        # Cancel stale orders
        for order_id in orders_to_cancel:
            try:
                success = await self._cancel_order_via_sidecar(order_id)
                if success:
                    self.active_orders[order_id].status = "cancelled"
                    self.stats["orders_cancelled"] += 1
                    logger.info(f"Cancelled stale order: {order_id}")
                else:
                    del self.active_orders[order_id]
            except Exception as e:
                logger.warning(f"Failed to cancel order {order_id}: {e}")
                del self.active_orders[order_id]
    
    async def _place_new_orders(self, bid_price: float, ask_price: float):
        """Place new orders if needed"""
        # Count active orders by side
        active_buys = sum(1 for order in self.active_orders.values() 
                         if order.side == "buy" and order.status == "active")
        active_sells = sum(1 for order in self.active_orders.values() 
                          if order.side == "sell" and order.status == "active")
        
        # Place buy order if needed
        if active_buys < self.max_orders_per_side:
            order_id = await self._place_order_via_sidecar("buy", bid_price, self.order_size)
            if order_id:
                self.active_orders[order_id] = OrderInfo(
                    order_id=order_id,
                    side="buy",
                    price=bid_price,
                    size=self.order_size,
                    timestamp=time.time()
                )
                self.stats["orders_placed"] += 1
                logger.info(f"🟢 BUY ORDER PLACED: {order_id} at {bid_price}")
        
        # Place sell order if needed
        if active_sells < self.max_orders_per_side:
            order_id = await self._place_order_via_sidecar("sell", ask_price, self.order_size)
            if order_id:
                self.active_orders[order_id] = OrderInfo(
                    order_id=order_id,
                    side="sell",
                    price=ask_price,
                    size=self.order_size,
                    timestamp=time.time()
                )
                self.stats["orders_placed"] += 1
                logger.info(f"🔴 SELL ORDER PLACED: {order_id} at {ask_price}")
    
    async def _place_order_via_sidecar(self, side: str, price: float, size: float) -> Optional[str]:
        """Place order via Swift sidecar"""
        try:
            # Create Swift order parameters
            swift_params = SwiftOrderParams(
                market_index=0,
                market_type="perp",
                side=side,
                price=price,
                size=size,
                taker_authority=str(self.keypair.pubkey()),
                sub_account_id=0,
                order_type="limit",
                post_only=True,
                reduce_only=False
            )
            
            # Create envelope
            envelope = self.envelope_creator.create_order_envelope(swift_params, self.keypair)
            
            # Send to sidecar
            response = self.sidecar_client.place_order(envelope)
            
            if response.get("status") == "accepted":
                return response.get("id", f"SWIFT-{int(time.time() * 1000000) % 999999:06d}")
            else:
                logger.error(f"Sidecar rejected order: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to place order via sidecar: {e}")
            return None
    
    async def _cancel_order_via_sidecar(self, order_id: str) -> bool:
        """Cancel order via Swift sidecar"""
        try:
            # Create cancel envelope
            envelope = self.envelope_creator.create_cancel_envelope(
                order_id, str(self.keypair.pubkey()), self.keypair
            )
            
            # Send to sidecar
            response = self.sidecar_client.cancel_order(order_id)
            
            return response.get("status") in ["cancelled", "accepted"]
            
        except Exception as e:
            logger.error(f"Failed to cancel order via sidecar: {e}")
            return False
    
    def get_stats(self) -> Dict[str, any]:
        """Get comprehensive statistics"""
        active_orders = sum(1 for order in self.active_orders.values() if order.status == "active")
        
        stats = self.stats.copy()
        stats.update({
            "active_orders": active_orders,
            "total_orders": len(self.active_orders),
            "swift_processor_stats": self.swift_processor.get_stats() if self.swift_processor else {}
        })
        
        return stats
    
    async def shutdown(self):
        """Shutdown the bot"""
        try:
            # Stop Swift receiver
            await self.swift_receiver.stop()
            
            # Cancel all active orders
            for order_id in list(self.active_orders.keys()):
                try:
                    await self._cancel_order_via_sidecar(order_id)
                except Exception:
                    pass
            
            # Close sidecar connection
            self.sidecar_client.close()
            
            logger.info("Bot shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

async def main():
    """Main function"""
    try:
        # Configuration
        config = {
            "env": os.getenv("DRIFT_ENV", "devnet"),
            "rpc_url": os.getenv("RPC_URL", "https://api.devnet.solana.com"),
            "sidecar_url": os.getenv("SWIFT_SIDECAR_URL", "http://localhost:8787"),
            "swift_websocket_url": os.getenv("SWIFT_WEBSOCKET_URL", "wss://swift.drift.trade/ws"),
            "wallet_file": ".valid_wallet.json",
            "order_size": 0.01,
            "max_orders_per_side": 1,
            "price_tolerance": 0.01,
            "spread_bps": 8
        }
        
        # Create and initialize bot
        bot = CompleteSwiftMMBot(config)
        
        if not await bot.initialize():
            logger.error("Failed to initialize bot")
            return 1
        
        # Start Swift receiver (with error handling)
        swift_success = await bot.start_swift_receiver()
        if not swift_success:
            logger.info("Running in market-making only mode (Swift reception disabled)")
        
        logger.info("🚀 Complete Swift MM Bot started!")
        logger.info(f"Order size: {config['order_size']} SOL")
        logger.info(f"Spread: {config['spread_bps']} bps")
        logger.info(f"Swift reception: {'✅ Enabled' if swift_success else '❌ Disabled'}")
        
        # Main loop
        tick_interval = 0.5  # 500ms
        stats_interval = 10  # 10 seconds
        last_stats = time.time()
        
        while True:
            try:
                # Market making tick
                await bot.market_making_tick()
                
                # Log stats periodically
                current_time = time.time()
                if current_time - last_stats >= stats_interval:
                    stats = bot.get_stats()
                    logger.info(f"📊 Stats: {stats}")
                    last_stats = current_time
                
                await asyncio.sleep(tick_interval)
                
            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(1)
        
        # Shutdown
        await bot.shutdown()
        return 0
        
    except Exception as e:
        logger.error(f"Bot failed: {e}")
        return 1

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
