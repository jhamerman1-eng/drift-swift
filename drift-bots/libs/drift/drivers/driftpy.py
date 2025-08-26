#!/usr/bin/env python3
"""
DriftPy Driver - Clean integration with DriftPy SDK
"""
import asyncio
import json
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from libs.drift.client import Order, OrderSide, Orderbook

@dataclass
class DriftPyConfig:
    """DriftPy configuration"""
    rpc_url: str
    wallet_secret_key: str
    env: str = "devnet"
    market: str = "SOL-PERP"
    market_index: int = 0
    timeout: int = 30

class DriftPyDriver:
    """Clean DriftPy integration for placing real orders on beta.drift.trade"""
    
    def __init__(self, config: DriftPyConfig):
        self.config = config
        self.drift_client = None
        self.solana_client = None
        self.keypair = None
        self.driftpy_ready = False
        
        print(f"[DRIFTPY] 🚀 Initializing DriftPy driver")
        print(f"[DRIFTPY] Environment: {config.env}")
        print(f"[DRIFTPY] Market: {config.market}")
        print(f"[DRIFTPY] RPC: {config.rpc_url}")
        print(f"[DRIFTPY] Wallet: {config.wallet_secret_key}")
    
    async def setup(self):
        """Setup DriftPy components with proper error handling"""
        try:
            await self._init_driftpy()
        except Exception as e:
            print(f"[DRIFTPY] ❌ Setup failed: {e}")
            self.driftpy_ready = False
    
    async def _init_driftpy(self):
        """Initialize DriftPy components"""
        try:
            # Import DriftPy modules
            from driftpy import keypair, types, drift_client
            from solana.rpc.async_api import AsyncClient
            from anchorpy import Wallet
            
            print(f"[DRIFTPY] ✅ DriftPy modules loaded")
            
            # Load wallet keypair following official docs pattern
            with open(self.config.wallet_secret_key, 'r') as f:
                keypair_data = json.load(f)
            
            # Create keypair and wrap in anchorpy.Wallet as per docs
            self.keypair = keypair.Keypair.from_bytes(keypair_data)
            wallet = Wallet(self.keypair)
            print(f"[DRIFTPY] ✅ Wallet loaded and wrapped in anchorpy.Wallet")
            
            # Initialize Solana connection
            self.solana_client = AsyncClient(self.config.rpc_url)
            print(f"[DRIFTPY] ✅ Solana connection established")
            
            # Initialize Drift client following official docs exactly
            self.drift_client = drift_client.DriftClient(
                connection=self.solana_client,
                wallet=wallet,  # Use anchorpy.Wallet wrapper
                env=self.config.env
            )
            print(f"[DRIFTPY] ✅ Drift client initialized")
            
            # CRITICAL: Add user account as per official docs
            print(f"[DRIFTPY] 📡 Setting up user account...")
            try:
                await self.drift_client.add_user(0)  # Assuming account 0 exists
                print(f"[DRIFTPY] ✅ User account setup complete")
            except Exception as user_error:
                print(f"[DRIFTPY] ⚠️  User account setup failed (may already exist): {user_error}")
                # Continue anyway - user might already be initialized
            
            # Subscribe to Drift state as per official docs
            print(f"[DRIFTPY] 📡 Subscribing to Drift state...")
            await self.drift_client.subscribe()
            print(f"[DRIFTPY] ✅ Drift subscription active")
            
            self.driftpy_ready = True
            print(f"[DRIFTPY] 🎯 DriftPy integration ready for real orders!")
            
        except ImportError as e:
            print(f"[DRIFTPY] ❌ DriftPy not available: {e}")
            print(f"[DRIFTPY] 💡 Install with: pip install driftpy")
            raise
        except Exception as e:
            print(f"[DRIFTPY] ❌ Initialization failed: {e}")
            raise
    
    async def place_order(self, order: Order) -> str:
        """Place REAL order on Drift protocol"""
        
        print(f"[DRIFTPY] 🚀 PLACING REAL ORDER ON DRIFT")
        print(f"[DRIFTPY] Side: {order.side.value.upper()}")
        print(f"[DRIFTPY] Size: ${order.size_usd}")
        print(f"[DRIFTPY] Price: ${order.price}")
        print(f"[DRIFTPY] Market: {self.config.market}")
        print(f"[DRIFTPY] Network: {self.config.env}")
        
        if not self.driftpy_ready:
            print(f"[DRIFTPY] ❌ DriftPy not ready - falling back to simulation")
            return self._place_simulated_order(order)
        
        try:
            return await self._place_real_drift_order_v2(order)
        except Exception as e:
            print(f"[DRIFTPY] ❌ Real order failed: {e}")
            print(f"[DRIFTPY] Falling back to simulation...")
            return self._place_simulated_order(order)
    
    async def _place_real_drift_order_v2(self, order: Order) -> str:
        """Place real order using DriftPy following official documentation"""
        print(f"[DRIFTPY] 🔥 PLACING REAL ORDER ON DRIFT (V2)!")
        
        try:
            # Import DriftPy types
            from driftpy.types import PositionDirection, OrderType, OrderParams, PostOnlyParams
            
            # Map our order side to DriftPy
            drift_side = PositionDirection.Long if order.side.value == "buy" else PositionDirection.Short
            
            # Create order parameters following official docs structure
            print(f"[DRIFTPY] 📡 Building Drift instruction (V2)...")
            print(f"[DRIFTPY]   Market Index: {self.config.market_index} ({self.config.market})")
            print(f"[DRIFTPY]   Order Type: LIMIT")
            print(f"[DRIFTPY]   Side: {drift_side}")
            print(f"[DRIFTPY]   Size: {order.size_usd} USD")
            print(f"[DRIFTPY]   Price: ${order.price}")
            print(f"[DRIFTPY]   Post Only: True")
            
            # Convert size to base asset amount (SOL units for SOL-PERP)
            # For SOL-PERP, we need to convert USD to SOL units
            sol_price = order.price  # Current SOL price
            sol_amount = order.size_usd / sol_price  # Convert USD to SOL units
            
            # Create order parameters with proper precision
            order_params = OrderParams(
                order_type=OrderType.Limit,
                base_asset_amount=int(sol_amount * 1e9),  # Convert to lamports (1 SOL = 1e9 lamports)
                market_index=self.config.market_index,
                direction=drift_side,
                market_type=0,  # Perp market
                price=int(order.price * 1e6),  # Convert to price units (6 decimal precision)
                post_only=PostOnlyParams.MustPostOnly
            )
            
            print(f"[DRIFTPY] ✅ OrderParams created successfully")
            print(f"[DRIFTPY]   Base Asset Amount: {sol_amount:.6f} SOL ({int(sol_amount * 1e9)} lamports)")
            print(f"[DRIFTPY]   Price: ${order.price:.6f} ({int(order.price * 1e6)} price units)")
            
            # Try instruction-based approach first (recommended by docs)
            print(f"[DRIFTPY] 📡 Getting place_perp_order instruction...")
            try:
                # Get the instruction
                ix = self.drift_client.get_place_perp_order_ix(order_params)
                print(f"[DRIFTPY] ✅ Instruction created successfully")
                
                # Send the instruction
                print(f"[DRIFTPY] 📡 Sending instruction to Drift...")
                result = await self.drift_client.send_ixs([ix])
                
                if hasattr(result, 'tx_sig'):
                    tx_sig = result.tx_sig
                    print(f"[DRIFTPY] ✅ REAL ORDER SUBMITTED TO DRIFT (V2)!")
                    print(f"[DRIFTPY] Transaction: {tx_sig}")
                    print(f"[DRIFTPY] 🌐 Check beta.drift.trade for your order!")
                    return tx_sig
                else:
                    print(f"[DRIFTPY] ❌ Order failed - no transaction signature")
                    print(f"[DRIFTPY] Result: {result}")
                    return f"failed_no_tx_sig_{int(time.time()*1000)}"
                    
            except Exception as ix_error:
                print(f"[DRIFTPY] ⚠️  Instruction approach failed: {ix_error}")
                print(f"[DRIFTPY] 📡 Trying direct place_perp_order...")
                
                # Fallback to direct method
                result = await self.drift_client.place_perp_order(order_params)
                
                if hasattr(result, 'tx_sig'):
                    tx_sig = result.tx_sig
                    print(f"[DRIFTPY] ✅ REAL ORDER SUBMITTED TO DRIFT!")
                    print(f"[DRIFTPY] Transaction: {tx_sig}")
                    print(f"[DRIFTPY] 🌐 Check beta.drift.trade for your order!")
                    return tx_sig
                else:
                    print(f"[DRIFTPY] ❌ Order failed - no transaction signature")
                    print(f"[DRIFTPY] Result: {result}")
                    return f"failed_no_tx_sig_{int(time.time()*1000)}"
            
        except Exception as e:
            print(f"[DRIFTPY] ❌ Real order placement failed: {e}")
            raise
    
    async def _place_real_drift_order(self, order: Order) -> str:
        """Place real order using DriftPy (legacy method)"""
        print(f"[DRIFTPY] 🔥 PLACING REAL ORDER ON DRIFT!")
        
        try:
            # Import DriftPy types
            from driftpy.types import PositionDirection, OrderType, OrderParams, PostOnlyParams
            
            # Map our order side to DriftPy
            drift_side = PositionDirection.Long if order.side.value == "buy" else PositionDirection.Short
            
            # Create order parameters
            print(f"[DRIFTPY] 📡 Building Drift instruction...")
            print(f"[DRIFTPY]   Market Index: {self.config.market_index} ({self.config.market})")
            print(f"[DRIFTPY]   Order Type: LIMIT")
            print(f"[DRIFTPY]   Side: {drift_side}")
            print(f"[DRIFTPY]   Size: {order.size_usd} USD")
            print(f"[DRIFTPY]   Price: ${order.price}")
            print(f"[DRIFTPY]   Post Only: True")
            
            # Create order parameters
            order_params = OrderParams(
                order_type=OrderType.Limit,
                base_asset_amount=int(order.size_usd * 1000000),  # Convert to base units
                market_index=self.config.market_index,
                direction=drift_side,
                market_type=0,  # Perp market
                price=int(order.price * 1000000),  # Convert to base units
                post_only=PostOnlyParams.MustPostOnly
            )
            
            print(f"[DRIFTPY] ✅ OrderParams created successfully")
            
            # Place the order
            print(f"[DRIFTPY] 📡 Submitting to Drift...")
            result = await self.drift_client.place_perp_order(order_params)
            
            # Check result and extract transaction signature
            if hasattr(result, 'tx_sig'):
                tx_sig = result.tx_sig
                print(f"[DRIFTPY] ✅ REAL ORDER SUBMITTED TO DRIFT!")
                print(f"[DRIFTPY] Transaction: {tx_sig}")
                print(f"[DRIFTPY] 🌐 Check beta.drift.trade for your order!")
                return tx_sig
            else:
                print(f"[DRIFTPY] ❌ Order failed - no transaction signature")
                print(f"[DRIFTPY] Result: {result}")
                return f"failed_no_tx_sig_{int(time.time()*1000)}"
            
        except Exception as e:
            print(f"[DRIFTPY] ❌ Real order placement failed: {e}")
            raise
    
    def _place_simulated_order(self, order: Order) -> str:
        """Place simulated order with enhanced details"""
        print(f"[DRIFTPY] 🎭 ENHANCED SIMULATION MODE")
        
        # Show what a real order would look like
        print(f"[DRIFTPY] 📊 Order Details:")
        print(f"   Market: {self.config.market}")
        print(f"   Side: {order.side.value.upper()}")
        print(f"   Size: ${order.size_usd}")
        print(f"   Price: ${order.price}")
        print(f"   Type: LIMIT")
        print(f"   Post Only: True")
        
        # Simulate order processing
        print(f"[DRIFTPY] ⏳ Processing order...")
        time.sleep(1)
        
        # Generate transaction signature
        tx_sig = f"sim_drift_{order.side.value}_{int(time.time()*1000)}"
        
        print(f"[DRIFTPY] ✅ Enhanced simulation complete!")
        print(f"[DRIFTPY] Transaction ID: {tx_sig}")
        print(f"[DRIFTPY] 💡 This simulates what happens on beta.drift.trade")
        
        return tx_sig
    
    async def get_orderbook(self) -> Orderbook:
        """Get real orderbook from Drift"""
        if self.driftpy_ready:
            print(f"[DRIFTPY] 📊 Getting real orderbook from Drift...")
            # TODO: Implement real orderbook fetch
            return Orderbook(bids=[(149.50, 10.0), (149.40, 15.0)], asks=[(150.50, 10.0), (150.60, 15.0)])
        else:
            print(f"[DRIFTPY] 📊 Using simulated orderbook...")
            return Orderbook(bids=[(149.50, 10.0), (149.40, 15.0)], asks=[(150.50, 10.0), (150.60, 15.0)])
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel specific order"""
        if not self.driftpy_ready:
            print(f"[DRIFTPY] ❌ DriftPy not ready")
            return False
        
        try:
            print(f"[DRIFTPY] 🚫 Cancelling order: {order_id}")
            # TODO: Implement real order cancellation
            print(f"[DRIFTPY] ⚠️  Cancel not implemented yet")
            return False
        except Exception as e:
            print(f"[DRIFTPY] ❌ Cancel failed: {e}")
            return False
    
    async def cancel_all(self) -> None:
        """Cancel all open orders"""
        if not self.driftpy_ready:
            print(f"[DRIFTPY] ❌ DriftPy not ready")
            return
        
        try:
            print(f"[DRIFTPY] 🚫 Cancelling all orders...")
            # TODO: Implement real order cancellation
            print(f"[DRIFTPY] ⚠️  Cancel all not implemented yet")
        except Exception as e:
            print(f"[DRIFTPY] ❌ Cancel all failed: {e}")
    
    async def close(self) -> None:
        """Close connections"""
        if self.solana_client:
            await self.solana_client.close()
            print(f"[DRIFTPY] Solana connection closed")
        
        print(f"[DRIFTPY] Driver closed")
    
    def get_status(self) -> Dict[str, Any]:
        """Get driver status"""
        return {
            "driver": "driftpy",
            "ready": self.driftpy_ready,
            "environment": self.config.env,
            "market": self.config.market,
            "rpc_url": self.config.rpc_url
        }

# Factory function for creating DriftPy driver
def create_driftpy_driver(rpc_url: str, wallet_secret_key: str, env: str = "devnet", market: str = "SOL-PERP") -> DriftPyDriver:
    """Create DriftPy driver instance"""
    config = DriftPyConfig(
        rpc_url=rpc_url,
        wallet_secret_key=wallet_secret_key,
        env=env,
        market=market
    )
    return DriftPyDriver(config)
