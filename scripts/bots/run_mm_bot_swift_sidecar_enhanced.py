#!/usr/bin/env python3
"""
Enhanced Market Making Bot using Swift Sidecar
Implements real order placement via Swift envelopes and proper order management
"""

import asyncio
import logging
import os
import sys
import time
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

from drift.swift_sidecar_driver import SwiftSidecarDriver
from drift.client import DriftpyClient
from drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
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

class SwiftSidecarExecutionClient:
    """Enhanced execution client using Swift sidecar with real order placement"""
    
    def __init__(self, sidecar_url: str, api_key: Optional[str] = None):
        self.sidecar = SwiftSidecarDriver(sidecar_url, api_key)
        self.envelope_creator = SwiftEnvelopeCreator()
        self.orders_received = 0
        self.orders_processed = 0
        self.keypair = None
        self.taker_authority = None
        
    async def initialize(self, keypair: Keypair):
        """Initialize with keypair for signing"""
        try:
            self.keypair = keypair
            self.taker_authority = str(keypair.pubkey())
            
            health = self.sidecar.health()
            logger.info(f"Swift sidecar health: {health}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Swift sidecar: {e}")
            return False
    
    async def place_order(self, order_params: Dict) -> Optional[str]:
        """Place order via Swift sidecar with real envelope creation"""
        try:
            if not self.keypair or not self.taker_authority:
                logger.error("Keypair or taker_authority not initialized")
                return None
                
            # Create Swift order parameters
            swift_params = SwiftOrderParams(
                market_index=0,  # SOL-PERP
                market_type="perp",
                side=order_params["side"],
                price=order_params["price"],
                size=order_params["size"],
                taker_authority=self.taker_authority,
                sub_account_id=0,
                order_type=order_params.get("order_type", "limit"),
                post_only=order_params.get("post_only", True),
                reduce_only=order_params.get("reduce_only", False)
            )
            
            # Create Swift envelope
            envelope = self.envelope_creator.create_order_envelope(swift_params, self.keypair)
            
            # Send to sidecar
            response = self.sidecar.place_order(envelope)
            
            if response.get("status") == "accepted":
                order_id = response.get("id", f"SWIFT-{int(time.time() * 1000000) % 999999:06d}")
                self.orders_processed += 1
                logger.info(f"Order placed via Swift sidecar: {order_id}")
                return order_id
            else:
                logger.error(f"Swift sidecar rejected order: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to place order via sidecar: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order via Swift sidecar"""
        try:
            if not self.keypair or not self.taker_authority:
                logger.error("Keypair or taker_authority not initialized")
                return False
                
            # Create cancel envelope
            envelope = self.envelope_creator.create_cancel_envelope(
                order_id, self.taker_authority, self.keypair
            )
            
            # Send to sidecar
            response = self.sidecar.cancel_order(order_id)
            
            if response.get("status") in ["cancelled", "accepted"]:
                logger.info(f"Order cancelled via Swift sidecar: {order_id}")
                return True
            else:
                logger.error(f"Swift sidecar failed to cancel order: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to cancel order via sidecar: {e}")
            return False
    
    async def close(self):
        """Clean up sidecar connection"""
        try:
            self.sidecar.close()
        except Exception:
            pass

class MarketDataAdapter:
    """Enhanced market data adapter with better error handling"""
    
    def __init__(self):
        self.drift_client = None
        self.last_orderbook = {"bids": [], "asks": []}
        self.last_update = 0
        
    def set_drift_client(self, drift_client):
        self.drift_client = drift_client
        
    async def get_orderbook(self) -> Dict[str, List]:
        """Get orderbook data with caching and fallback"""
        try:
            current_time = time.time()
            
            # Use cached data if recent enough
            if current_time - self.last_update < 0.1:  # 100ms cache
                return self.last_orderbook
            
            if self.drift_client:
                try:
                    # Try to get real orderbook
                    ob = await self.drift_client.get_l2_orderbook_compat("SOL-PERP", 10)
                    if ob and ob.get("bids") and ob.get("asks"):
                        self.last_orderbook = ob
                        self.last_update = current_time
                        return ob
                except Exception as e:
                    logger.debug(f"Failed to get real orderbook: {e}")
            
            # Return cached orderbook if available
            if self.last_orderbook.get("bids") and self.last_orderbook.get("asks"):
                return self.last_orderbook
                
            # Fallback to mock data
            logger.warning("Using mock orderbook data")
            mock_price = 200.0
            spread = 0.1
            return {
                "bids": [[mock_price - spread/2, 1.0]],
                "asks": [[mock_price + spread/2, 1.0]]
            }
            
        except Exception as e:
            logger.warning(f"Orderbook fetch failed: {e}, using mock")
            return self.last_orderbook

class JITMarketMaker:
    """Enhanced Just-in-time market maker with proper order management"""
    
    def __init__(self, market_data: MarketDataAdapter, execution: SwiftSidecarExecutionClient):
        self.md = market_data
        self.execution = execution
        self.drift_client = None
        self.keypair = None
        self.order_size = 0.01  # Reduced for current balance
        self.active_orders: Dict[str, OrderInfo] = {}
        self.max_orders_per_side = 1
        self.price_tolerance = 0.01  # Cancel if price moves more than this
        
    def initialize(self, drift_client, keypair):
        self.drift_client = drift_client
        self.keypair = keypair
        self.md.set_drift_client(drift_client)
        
    async def tick(self):
        """Main market making tick with enhanced logic"""
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
            
            # Calculate our spread (adaptive based on market spread)
            market_spread = best_ask - best_bid
            our_spread = max(market_spread * 0.1, 0.01)  # 10% of market spread or 0.01 minimum
            
            # Calculate our prices
            bid_price = mid_price - our_spread / 2
            ask_price = mid_price + our_spread / 2
            
            # Round to reasonable precision
            bid_price = round(bid_price, 4)
            ask_price = round(ask_price, 4)
            
            logger.info(f"Market making tick: bid={bid_price}, ask={ask_price}, spread={our_spread:.4f}")
            
            # Manage orders with enhanced logic
            await self.manage_orders(bid_price, ask_price)
            
        except Exception as e:
            logger.error(f"Error in market making tick: {e}")
    
    async def manage_orders(self, bid_price: float, ask_price: float):
        """Enhanced order management with proper tracking"""
        try:
            # Check if we need to cancel orders due to price movement
            await self._cancel_stale_orders(bid_price, ask_price)
            
            # Place new orders if needed
            await self._place_new_orders(bid_price, ask_price)
            
        except Exception as e:
            logger.error(f"Error managing orders: {e}")
    
    async def _cancel_stale_orders(self, bid_price: float, ask_price: float):
        """Cancel orders that are too far from current market prices"""
        orders_to_cancel = []
        
        for order_id, order_info in self.active_orders.items():
            if order_info.status != "active":
                continue
                
            current_price = bid_price if order_info.side == "buy" else ask_price
            price_diff = abs(current_price - order_info.price)
            
            # Cancel if price moved too much or order is too old
            age_seconds = time.time() - order_info.timestamp
            if price_diff > self.price_tolerance or age_seconds > 30:  # 30 second max age
                orders_to_cancel.append(order_id)
        
        # Cancel stale orders
        for order_id in orders_to_cancel:
            try:
                success = await self.execution.cancel_order(order_id)
                if success:
                    self.active_orders[order_id].status = "cancelled"
                    logger.info(f"Cancelled stale order: {order_id}")
                else:
                    # Remove from tracking if cancellation failed
                    del self.active_orders[order_id]
            except Exception as e:
                logger.warning(f"Failed to cancel order {order_id}: {e}")
                del self.active_orders[order_id]
    
    async def _place_new_orders(self, bid_price: float, ask_price: float):
        """Place new orders if we don't have active ones"""
        # Count active orders by side
        active_buys = sum(1 for order in self.active_orders.values() 
                         if order.side == "buy" and order.status == "active")
        active_sells = sum(1 for order in self.active_orders.values() 
                          if order.side == "sell" and order.status == "active")
        
        # Place buy order if needed
        if active_buys < self.max_orders_per_side and bid_price > 0:
            order_id = await self.place_order("buy", bid_price, self.order_size)
            if order_id:
                self.active_orders[order_id] = OrderInfo(
                    order_id=order_id,
                    side="buy",
                    price=bid_price,
                    size=self.order_size,
                    timestamp=time.time()
                )
                logger.info(f"🟢 LIVE BUY ORDER ACTIVE: {order_id} at {bid_price}")
        
        # Place sell order if needed
        if active_sells < self.max_orders_per_side and ask_price > 0:
            order_id = await self.place_order("sell", ask_price, self.order_size)
            if order_id:
                self.active_orders[order_id] = OrderInfo(
                    order_id=order_id,
                    side="sell",
                    price=ask_price,
                    size=self.order_size,
                    timestamp=time.time()
                )
                logger.info(f"🔴 LIVE SELL ORDER ACTIVE: {order_id} at {ask_price}")
    
    async def place_order(self, side: str, price: float, size: float) -> Optional[str]:
        """Place order via execution client"""
        try:
            order_params = {
                "side": side,
                "price": price,
                "size": size,
                "market": "SOL-PERP",
                "order_type": "limit",
                "post_only": True,
                "reduce_only": False
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
    
    def get_stats(self) -> Dict[str, int]:
        """Get market maker statistics"""
        active_count = sum(1 for order in self.active_orders.values() if order.status == "active")
        return {
            "active_orders": active_count,
            "total_orders_placed": len(self.active_orders),
            "orders_received": self.execution.orders_received,
            "orders_processed": self.execution.orders_processed
        }

async def run_main():
    """Main bot loop with enhanced error handling"""
    try:
        # Load configuration
        env = os.getenv("DRIFT_ENV", "beta")
        config_file = os.getenv("DRIFT_CONFIG", "configs/core/drift_client.yaml")
        
        logger.info(f"Starting Enhanced MM Bot with env={env}, config={config_file}")
        
        # Load wallet
        wallet_file = ".valid_wallet.json"
        if not os.path.exists(wallet_file):
            logger.error(f"Wallet file not found: {wallet_file}")
            return 1
            
        with open(wallet_file, 'r') as f:
            wallet_data = json.load(f)
        
        # Create keypair from wallet data
        if isinstance(wallet_data, list):
            secret_key = bytes(wallet_data)
        else:
            secret_key = bytes(wallet_data["secret_key"])
        
        keypair = Keypair.from_bytes(secret_key)
        logger.info(f"Wallet loaded: {keypair.pubkey()}")
        
        # Initialize drift client
        drift_client = DriftpyClient(
            cfg={"rpc_url": "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494", "env": "devnet"},
            env="devnet"
        )
        
        # Initialize Swift sidecar
        sidecar_url = os.getenv("SWIFT_SIDECAR_URL", "http://localhost:8787")
        execution = SwiftSidecarExecutionClient(sidecar_url)
        
        # Initialize market data
        market_data = MarketDataAdapter()
        
        # Initialize market maker
        mm = JITMarketMaker(market_data, execution)
        
        # Initialize components
        await drift_client.connect()
        await execution.initialize(keypair)
        mm.initialize(drift_client, keypair)
        
        logger.info("Enhanced MM Bot initialized successfully")
        logger.info(f"Order size: {mm.order_size} SOL")
        logger.info(f"Max orders per side: {mm.max_orders_per_side}")
        
        # Main loop
        tick_interval = 0.5  # 500ms
        stats_interval = 10  # 10 seconds
        last_stats = time.time()
        
        while True:
            try:
                await mm.tick()
                
                # Log stats periodically
                current_time = time.time()
                if current_time - last_stats >= stats_interval:
                    stats = mm.get_stats()
                    logger.info(f"Stats: {stats}")
                    last_stats = current_time
                
                await asyncio.sleep(tick_interval)
                
            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(1)
                
    except Exception as e:
        logger.error(f"Failed to start Enhanced MM Bot: {e}")
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



