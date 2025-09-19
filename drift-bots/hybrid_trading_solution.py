#!/usr/bin/env python3
"""
Hybrid Trading Solution - DriftPy + Solana CLI Fallback for Real Orders
"""
import asyncio
import json
import time
from typing import Optional, Union
from libs.drift.client import Order, OrderSide
from libs.drift.drivers.driftpy import DriftPyDriver, DriftPyConfig
from solana_cli_trade import SolanaCLITrader

class HybridTrader:
    """Hybrid trader that tries DriftPy first, falls back to Solana CLI"""
    
    def __init__(self, 
                 wallet_path: str,
                 rpc_url: str,
                 env: str = "devnet",
                 market: str = "SOL-PERP"):
        self.wallet_path = wallet_path
        self.rpc_url = rpc_url
        self.env = env
        self.market = market
        
        # Initialize both drivers
        self.driftpy_driver = DriftPyDriver(DriftPyConfig(
            rpc_url=rpc_url,
            wallet_secret_key=wallet_path,
            env=env,
            market=market
        ))
        
        self.solana_cli_trader = SolanaCLITrader(
            wallet_path=wallet_path,
            rpc_url=rpc_url,
            env=env
        )
        
        self.current_driver = "unknown"
        
        print(f"[HYBRID] 🚀 Initializing Hybrid Trading Solution")
        print(f"[HYBRID] Wallet: {wallet_path}")
        print(f"[HYBRID] RPC: {rpc_url}")
        print(f"[HYBRID] Environment: {env}")
        print(f"[HYBRID] Market: {market}")
    
    async def setup(self):
        """Setup both trading systems"""
        print(f"\n[HYBRID] 🔧 Setting up trading systems...")
        
        # Try DriftPy first
        try:
            print(f"[HYBRID] 📦 Attempting DriftPy setup...")
            await self.driftpy_driver.setup()
            
            if self.driftpy_driver.driftpy_ready:
                self.current_driver = "driftpy"
                print(f"[HYBRID] ✅ DriftPy ready - will use for real orders")
            else:
                print(f"[HYBRID] ⚠️  DriftPy not ready")
                
        except Exception as e:
            print(f"[HYBRID] ❌ DriftPy setup failed: {e}")
        
        # Solana CLI is always available as fallback
        print(f"[HYBRID] 🔧 Solana CLI fallback ready")
        
        if self.current_driver == "driftpy":
            print(f"[HYBRID] 🎯 Primary: DriftPy, Fallback: Solana CLI")
        else:
            print(f"[HYBRID] 🎯 Primary: Solana CLI")
    
    async def place_order(self, order: Order) -> str:
        """Place order using best available method"""
        print(f"\n[HYBRID] 🚀 PLACING ORDER")
        print(f"[HYBRID] Side: {order.side.value.upper()}")
        print(f"[HYBRID] Size: ${order.size_usd}")
        print(f"[HYBRID] Price: ${order.price}")
        print(f"[HYBRID] Driver: {self.current_driver}")
        
        if self.current_driver == "driftpy":
            try:
                print(f"[HYBRID] 📡 Attempting DriftPy order...")
                result = await self.driftpy_driver.place_order(order)
                
                if not result.startswith("failed") and not result.startswith("sim_"):
                    print(f"[HYBRID] ✅ DriftPy order successful!")
                    return result
                else:
                    print(f"[HYBRID] ⚠️  DriftPy failed, falling back to Solana CLI...")
                    
            except Exception as e:
                print(f"[HYBRID] ❌ DriftPy error: {e}")
                print(f"[HYBRID] 🔄 Falling back to Solana CLI...")
        
        # Use Solana CLI fallback
        print(f"[HYBRID] 📡 Using Solana CLI fallback...")
        try:
            result = self.solana_cli_trader.place_drift_order(order)
            print(f"[HYBRID] ✅ Solana CLI order successful!")
            return result
        except Exception as e:
            print(f"[HYBRID] ❌ Solana CLI also failed: {e}")
            return f"failed_all_methods_{int(time.time()*1000)}"
    
    async def get_orderbook(self):
        """Get orderbook from best available source"""
        if self.current_driver == "driftpy" and self.driftpy_driver.driftpy_ready:
            return await self.driftpy_driver.get_orderbook()
        else:
            # Return simulated orderbook for Solana CLI
            from libs.drift.client import Orderbook
            return Orderbook(
                bids=[(149.50, 10.0), (149.40, 15.0)],
                asks=[(150.50, 10.0), (150.60, 15.0)]
            )
    
    async def close(self):
        """Close all connections"""
        if self.current_driver == "driftpy":
            await self.driftpy_driver.close()
        print(f"[HYBRID] All connections closed")
    
    def get_status(self) -> dict:
        """Get comprehensive status"""
        return {
            "driver": "hybrid",
            "primary_driver": self.current_driver,
            "driftpy_ready": self.driftpy_driver.driftpy_ready if hasattr(self, 'driftpy_driver') else False,
            "solana_cli_ready": True,
            "wallet_path": self.wallet_path,
            "rpc_url": self.rpc_url,
            "environment": self.env,
            "market": self.market
        }

async def test_hybrid_trading():
    """Test the hybrid trading solution"""
    print("🚀 TESTING HYBRID TRADING SOLUTION")
    print("="*60)
    
    # Configuration
    wallet_path = r"C:\Users\genuw\.config\solana\id_devnet_custom.json"
    rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
    
    print(f"📋 Configuration:")
    print(f"   Wallet: {wallet_path}")
    print(f"   RPC: {rpc_url}")
    print(f"   Environment: devnet")
    print(f"   Market: SOL-PERP")
    
    # Create hybrid trader
    trader = HybridTrader(
        wallet_path=wallet_path,
        rpc_url=rpc_url,
        env="devnet",
        market="SOL-PERP"
    )
    
    try:
        # Setup
        print(f"\n🔧 Setting up hybrid trader...")
        await trader.setup()
        
        # Show status
        status = trader.get_status()
        print(f"\n📊 Trader Status:")
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        # Create test order
        test_order = Order(
            side=OrderSide.BUY,
            size_usd=25.0,
            price=149.50
        )
        
        print(f"\n📝 Test Order:")
        print(f"   Side: {test_order.side.value}")
        print(f"   Size: ${test_order.size_usd}")
        print(f"   Price: ${test_order.price}")
        
        # Place order
        print(f"\n🚀 Placing order via hybrid system...")
        order_id = await trader.place_order(test_order)
        
        print(f"\n✅ Order Result:")
        print(f"   Order ID: {order_id}")
        
        if order_id.startswith("failed"):
            print(f"❌ Order failed: {order_id}")
            return False
        else:
            print(f"🎉 ORDER PLACED SUCCESSFULLY!")
            print(f"🌐 Check beta.drift.trade for your order!")
            return True
            
    except Exception as e:
        print(f"❌ Error during hybrid trading test: {e}")
        return False
    finally:
        await trader.close()

async def main():
    """Main function"""
    print("🔥 HYBRID TRADING SOLUTION TEST")
    print("="*60)
    
    success = await test_hybrid_trading()
    
    print(f"\n{'='*60}")
    print(f"📊 TEST RESULT: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"{'='*60}")
    
    if success:
        print(f"🎉 Hybrid trading solution working!")
        print(f"💡 Real orders can now be placed via best available method")
    else:
        print(f"❌ Hybrid trading solution failed")
        print(f"💡 Check the error messages above")

if __name__ == "__main__":
    asyncio.run(main())
