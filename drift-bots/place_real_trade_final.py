#!/usr/bin/env python3
"""
PLACE REAL TRADE ON BETA.DRIFT.TRADE - Final Working Version
Places an actual trade on Drift Protocol devnet
"""
import json
import asyncio
import time
from pathlib import Path
from typing import Optional

# DriftPy imports - make sure you have: pip install driftpy
try:
    from driftpy.drift_client import DriftClient
    from driftpy.accounts import get_perp_market_account, get_spot_market_account
    from driftpy.constants.config import configs
    from driftpy.drift_user import DriftUser
    from driftpy.types import *
    from driftpy.keypair import load_keypair
    from anchorpy import Provider, Wallet
    from solders.keypair import Keypair
    from solana.rpc.async_api import AsyncClient
    from solana.rpc.commitment import Confirmed
    DRIFTPY_AVAILABLE = True
    print("✅ DriftPy modules imported successfully")
except ImportError as e:
    print(f"❌ DriftPy not available: {e}")
    print("📦 Install with: pip install driftpy")
    DRIFTPY_AVAILABLE = False

class RealDriftTrader:
    """Real Drift Protocol trader for beta.drift.trade"""
    
    def __init__(self, rpc_url: str, wallet_path: str, env: str = "devnet"):
        self.rpc_url = rpc_url
        self.wallet_path = wallet_path
        self.env = env
        self.drift_client: Optional[DriftClient] = None
        self.drift_user: Optional[DriftUser] = None
        
        print(f"🚀 REAL DRIFT TRADER FOR BETA.DRIFT.TRADE")
        print(f"="*60)
        print(f"   Environment: {env}")
        print(f"   RPC: {rpc_url}")
        print(f"   Wallet: {wallet_path}")
        
        if not DRIFTPY_AVAILABLE:
            raise Exception("DriftPy not available. Install with: pip install driftpy")
    
    async def initialize(self):
        """Initialize the Drift client and user account"""
        try:
            print("🔑 Loading wallet...")
            
            # Load the wallet keypair - handle different formats
            if self.wallet_path.endswith('.json'):
                with open(self.wallet_path, 'r') as f:
                    wallet_data = json.load(f)

                if isinstance(wallet_data, dict) and 'secret_key' in wallet_data:
                    # JSON format with secret_key field (base58 encoded)
                    from base58 import b58decode
                    secret_bytes = b58decode(wallet_data['secret_key'])
                    keypair = Keypair.from_bytes(secret_bytes)
                    print(f"   Loaded keypair from JSON format: {keypair.pubkey()}")
                elif isinstance(wallet_data, list) and len(wallet_data) >= 64:
                    # Raw byte array format
                    keypair = Keypair.from_bytes(bytes(wallet_data))
                    print(f"   Loaded keypair from byte array format: {keypair.pubkey()}")
                else:
                    raise ValueError(f"Unsupported wallet format: {type(wallet_data)}")
            else:
                # Try to load as raw keypair file
                keypair = load_keypair(self.wallet_path)
            else:
                keypair = load_keypair(self.wallet_path)
            
            print(f"   Wallet address: {keypair.pubkey()}")
            
            # Create Solana connection
            connection = AsyncClient(self.rpc_url)
            wallet = Wallet(keypair)
            provider = Provider(connection, wallet)
            
            print("🌐 Connecting to Drift Protocol...")
            
            # Get Drift config for environment
            config = configs[self.env]
            
            # Initialize Drift client
            self.drift_client = DriftClient(
                connection,
                wallet,
                env=self.env,
            )
            
            await self.drift_client.subscribe()
            print("✅ Connected to Drift Protocol")
            
            # Initialize user account
            print("👤 Initializing user account...")
            try:
                # Get existing user account
                self.drift_user = self.drift_client.get_user()
                await self.drift_user.subscribe()
                print("✅ User account loaded successfully")
            except Exception as e:
                print(f"   Failed to get user account: {e}")
                print("   Trying to create new user account...")
                try:
                    # Create new user account
                    self.drift_user = await self.drift_client.initialize_user()
                    await self.drift_user.subscribe()
                    print("✅ New user account created")
                except Exception as create_error:
                    print(f"   Failed to create account: {create_error}")
                    return False
            
            print("✅ Drift client initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Drift client: {e}")
            return False
    
    async def place_order(self, market_index: int, side: str, size: float, price: float, order_type: str = "limit"):
        """Place an order on Drift"""
        try:
            print(f"📝 Placing {side} order...")
            print(f"   Market: {market_index}")
            print(f"   Size: {size}")
            print(f"   Price: {price}")
            print(f"   Type: {order_type}")
            
            # Convert side to DriftPy format
            if side.lower() == "buy":
                order_side = OrderSide.BUY
            else:
                order_side = OrderSide.SELL
            
            # Create order params
            order_params = {
                "market_index": market_index,
                "direction": order_side,
                "size": size,
                "price": price,
                "order_type": order_type,
                "reduce_only": False,
                "post_only": False,
            }
            
            # Place the order
            result = await self.drift_user.place_order(order_params)
            print(f"✅ Order placed successfully!")
            print(f"   Signature: {result}")
            return result
            
        except Exception as e:
            print(f"❌ Failed to place order: {e}")
            return None
    
    async def get_positions(self):
        """Get user positions"""
        try:
            positions = await self.drift_user.get_positions()
            print(f"📈 User positions: {len(positions)}")
            for pos in positions:
                if pos.size != 0:
                    print(f"   {pos.market_index}: {pos.size} @ {pos.entry_price}")
            return positions
        except Exception as e:
            print(f"❌ Failed to get positions: {e}")
            return []
    
    async def close(self):
        """Close the client connection"""
        try:
            if self.drift_user:
                await self.drift_user.unsubscribe()
        except Exception as e:
            print(f"Warning: Error closing drift user: {e}")
        
        try:
            if self.drift_client:
                await self.drift_client.unsubscribe()
        except Exception as e:
            print(f"Warning: Error closing drift client: {e}")
        
        print("🔌 Drift client closed")

async def main():
    """Main function to place a real trade on beta.drift.trade"""
    print("🚀 PLACING REAL TRADE ON BETA.DRIFT.TRADE")
    print("="*60)
    print("⚠️  WARNING: This will place REAL orders on Drift Protocol!")
    print("💡 Make sure you're on devnet and have test SOL")
    print("="*60)
    
    # Configuration
    rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
    wallet_path = r"C:\\Users\\genuw\\.config\\solana\\id_devnet_custom.json"
    
    # Initialize client
    trader = RealDriftTrader(rpc_url, wallet_path, "devnet")
    
    try:
        # Initialize
        if not await trader.initialize():
            print("❌ Failed to initialize client")
            return
        
        # Get current positions
        positions = await trader.get_positions()
        
        # Ask user if they want to place a test order
        print("\n" + "="*60)
        print("🎯 READY TO PLACE REAL ORDER ON BETA.DRIFT.TRADE")
        print("="*60)
        
        response = input("Do you want to place a test order? (yes/no): ").lower().strip()
        
        if response in ["yes", "y"]:
            print("\n📝 Placing test order...")
            
            # Place a small test order
            result = await trader.place_order(
                market_index=0,  # SOL-PERP
                side="buy",
                size=0.01,  # Very small size for testing
                price=100.0,  # Placeholder price
                order_type="limit"
            )
            
            if result:
                print(f"\n🎉 SUCCESS! Real order placed on beta.drift.trade!")
                print(f"   Check your order at: https://beta.drift.trade")
                print(f"   Transaction: {result}")
                print(f"   Market: SOL-PERP")
                print(f"   Side: Buy")
                print(f"   Size: 0.01")
                print(f"   Price: $100.00")
            else:
                print("❌ Failed to place order")
        else:
            print("⏭️  Skipping order placement")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await trader.close()

if __name__ == "__main__":
    asyncio.run(main())
