#!/usr/bin/env python3
"""
Simple Drift Trader - Direct Blockchain Trading
Places real orders on Drift protocol using DriftPy
"""

import asyncio
import logging
import os
import sys
import time
import json
from typing import Dict, Optional, Any

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SimpleDriftTrader:
    """Simple Drift trader for direct blockchain trading"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.drift_client = None
        self.keypair = None
        self.current_position = 0.0
        self.active_orders = {}
        
    async def initialize(self):
        """Initialize DriftPy client"""
        try:
            # Load wallet
            await self._load_wallet()
            
            # Initialize DriftPy client
            await self._initialize_drift_client()
            
            logger.info("✅ Simple Drift Trader initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize trader: {e}")
            return False
    
    async def _load_wallet(self):
        """Load wallet from file"""
        wallet_file = self.config.get("wallet_file", ".valid_wallet.json")
        
        if not os.path.exists(wallet_file):
            raise FileNotFoundError(f"Wallet file not found: {wallet_file}")
        
        with open(wallet_file, 'r') as f:
            wallet_data = json.load(f)
        
        if isinstance(wallet_data, list):
            # Array format
            self.keypair = Keypair.from_bytes(bytes(wallet_data))
        else:
            # Object format
            self.keypair = Keypair.from_bytes(bytes(wallet_data["secretKey"]))
        
        logger.info(f"Wallet loaded: {self.keypair.pubkey()}")
    
    async def _initialize_drift_client(self):
        """Initialize DriftPy client"""
        from driftpy.drift_client import DriftClient
        
        rpc_url = self.config.get("rpc_url", "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")
        env = self.config.get("env", "devnet")
        
        if self.keypair is None:
            raise RuntimeError("Keypair not loaded")
        
        self.drift_client = DriftClient(
            connection=AsyncClient(rpc_url),
            wallet=self.keypair,
            env=env
        )
        
        # Add user and subscribe
        await self.drift_client.add_user(0)
        await self.drift_client.subscribe()
        
        logger.info(f"DriftPy client connected to {env}")
    
    async def place_order(self, side: str, price: float, size: float) -> Optional[str]:
        """Place order directly on Drift blockchain"""
        try:
            if not self.drift_client or not self.keypair:
                logger.error("Drift client or keypair not available")
                return None
            
            # Convert to DriftPy format
            market_index = 0  # SOL-PERP
            order_side = "Long" if side == "buy" else "Short"
            
            # Convert size to base asset amount (SOL has 9 decimals)
            base_asset_amount = int(size * 1_000_000_000)  # SOL has 9 decimals
            
            logger.info(f"🚀 Placing {order_side} order: {size} SOL @ ${price:.4f}")
            logger.info(f"   Base amount: {base_asset_amount}")
            
            # Import DriftPy types
            from driftpy.types import OrderParams, OrderType, PositionDirection, MarketType, PostOnlyParams
            # Convert to DriftPy format
            direction = PositionDirection.Long() if side == "buy" else PositionDirection.Short()  # type: ignore
            price_precise = int(price * 1_000_000)  # Convert to price precision (6 decimals)

            # Create OrderParams object
            order_params = OrderParams(
                order_type=OrderType.Limit(),  # type: ignore
                base_asset_amount=base_asset_amount,
                market_index=market_index,
                direction=direction,
                price=price_precise,
                market_type=MarketType.Perp(),  # type: ignore
                reduce_only=False,
                post_only=PostOnlyParams.TryPostOnly()  # type: ignore
            )
            
            # Place order using DriftPy
            result = await self.drift_client.place_perp_order(order_params)
            
            if result:
                order_id = str(result)
                logger.info(f"✅ Order placed successfully: {order_id}")
                logger.info(f"🔗 View on Solana Explorer: https://explorer.solana.com/tx/{order_id}?cluster=devnet")
                return order_id
            else:
                logger.error(f"Failed to place order: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to place order on blockchain: {e}")
            return None
    
    async def get_position(self) -> float:
        """Get current SOL-PERP position"""
        try:
            if not self.drift_client:
                return 0.0
            
            drift_user = self.drift_client.get_user()
            perp_positions = drift_user.get_active_perp_positions()
            
            for pos in perp_positions:
                if pos.market_index == 0:  # SOL-PERP
                    # Convert from BASE_PRECISION to SOL
                    sol_position = float(pos.base_asset_amount) / 1_000_000_000
                    return sol_position
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return 0.0
    
    async def market_making_tick(self):
        """Simple market making tick"""
        try:
            # Get current position
            self.current_position = await self.get_position()
            
            # Get current price (simplified - using a fixed price for demo)
            current_price = 241.50  # This should come from oracle or orderbook
            
            # Calculate spread
            spread = 0.1  # 10 cents spread
            buy_price = current_price - spread/2
            sell_price = current_price + spread/2
            
            # Place buy order
            buy_order_id = await self.place_order("buy", buy_price, 0.01)
            if buy_order_id:
                self.active_orders[buy_order_id] = {
                    "side": "buy",
                    "price": buy_price,
                    "size": 0.01,
                    "timestamp": time.time()
                }
            
            # Place sell order
            sell_order_id = await self.place_order("sell", sell_price, 0.01)
            if sell_order_id:
                self.active_orders[sell_order_id] = {
                    "side": "sell", 
                    "price": sell_price,
                    "size": 0.01,
                    "timestamp": time.time()
                }
            
            logger.info(f"📊 Position: {self.current_position:.6f} SOL, Active orders: {len(self.active_orders)}")
            
        except Exception as e:
            logger.error(f"Error in market making tick: {e}")

async def main():
    """Main function"""
    try:
        # Configuration
        config = {
            "env": "devnet",
            "rpc_url": "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
            "wallet_file": ".valid_wallet.json",
        }
        
        # Create and initialize trader
        trader = SimpleDriftTrader(config)
        
        if not await trader.initialize():
            logger.error("Failed to initialize trader")
            return 1
        
        logger.info("🚀 Simple Drift Trader started!")
        logger.info("🔗 Trading on Drift devnet with Helius RPC")
        logger.info("📊 Orders will appear on Drift UI")
        
        # Main trading loop
        tick_interval = 5.0  # 5 seconds between ticks
        tick_count = 0
        
        while True:
            try:
                tick_count += 1
                logger.info(f"🔄 Tick {tick_count}")
                
                await trader.market_making_tick()
                
                await asyncio.sleep(tick_interval)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(tick_interval)
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
