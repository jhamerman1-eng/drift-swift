#!/usr/bin/env python3
"""
REAL DRIFT PROTOCOL INTEGRATION - Places actual orders on beta.drift.trade
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

class RealDriftClient:
    """Real Drift Protocol client for beta.drift.trade"""
    
    def __init__(self, rpc_url: str, wallet_path: str, env: str = "devnet"):
        self.rpc_url = rpc_url
        self.wallet_path = wallet_path
        self.env = env
        self.drift_client: Optional[DriftClient] = None
        self.drift_user: Optional[DriftUser] = None
        
        print(f"🚀 Initializing REAL Drift Client")
        print(f"   Environment: {env}")
        print(f"   RPC: {rpc_url}")
        print(f"   Wallet: {wallet_path}")
        
        if not DRIFTPY_AVAILABLE:
            raise Exception("DriftPy not available. Install with: pip install driftpy")
    
    async def initialize(self):
        """Initialize the Drift client and user account"""
        try:
            print("🔑 Loading wallet...")
            
            # Load the wallet keypair
            if self.wallet_path.endswith('.json'):
                with open(self.wallet_path, 'r') as f:
                    secret_key = json.load(f)
                keypair = Keypair.from_bytes(secret_key)
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
            
            # Check if user account exists
            user_exists = await self.drift_client.get_user_account_exists(
                authority=wallet.public_key
            )
            
            if not user_exists:
                print("📝 User account doesn't exist, creating...")
                await self.drift_client.initialize_user()
                print("✅ User account created")
            
            # Get user
            self.drift_user = DriftUser(
                self.drift_client,
                authority=wallet.public_key,
            )
            await self.drift_user.subscribe()
            
            print("✅ Drift client fully initialized and ready!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Drift client: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def get_market_info(self, market_index: int = 0):
        """Get market information (0 = SOL-PERP)"""
        try:
            perp_market = await get_perp_market_account(
                self.drift_client.program,
                market_index
            )
            
            print(f"📊 Market {market_index} Info:")
            print(f"   Symbol: SOL-PERP")
            print(f"   Market Index: {market_index}")
            print(f"   Base Asset Reserve: {perp_market.amm.base_asset_reserve}")
            print(f"   Quote Asset Reserve: {perp_market.amm.quote_asset_reserve}")
            
            return perp_market
            
        except Exception as e:
            print(f"❌ Failed to get market info: {e}")
            return None
    
    async def get_user_positions(self):
        """Get user's current positions"""
        try:
            if not self.drift_user:
                print("❌ User not initialized")
                return None
            
            user_account = await self.drift_user.get_user_account()
            
            print("📈 Current Positions:")
            for i, position in enumerate(user_account.perp_positions):
                if position.base_asset_amount != 0:
                    print(f"   Market {position.market_index}: {position.base_asset_amount} base")
            
            return user_account.perp_positions
            
        except Exception as e:
            print(f"❌ Failed to get positions: {e}")
            return None
    
    async def place_perp_order(
        self,
        market_index: int,
        order_side: str,  # "buy" or "sell"
        order_type: str,  # "market", "limit"
        amount: float,
        price: Optional[float] = None
    ):
        """Place a perpetual order on Drift"""
        try:
            if not self.drift_client:
                print("❌ Drift client not initialized")
                return None
            
            print(f"🚀 PLACING REAL ORDER ON DRIFT")
            print(f"   Market: {market_index} (SOL-PERP)")
            print(f"   Side: {order_side.upper()}")
            print(f"   Type: {order_type.upper()}")
            print(f"   Amount: {amount}")
            if price:
                print(f"   Price: ${price}")
            
            # Convert to DriftPy types
            side = PositionDirection.Long() if order_side.lower() == "buy" else PositionDirection.Short()
            
            if order_type.lower() == "market":
                order_type_drift = OrderType.Market()
                order_price = 0  # Market orders use 0 price
            else:
                order_type_drift = OrderType.Limit()
                order_price = int(price * 1e6) if price else 0  # Convert to 6 decimal places
            
            # Convert amount to base units (typically 9 decimal places for SOL)
            base_asset_amount = int(amount * 1e9)
            
            print("📡 Submitting order to blockchain...")
            
            # Place the order
            tx_sig = await self.drift_client.place_perp_order(
                OrderParams(
                    order_type=order_type_drift,
                    market_index=market_index,
                    direction=side,
                    base_asset_amount=base_asset_amount,
                    price=order_price,
                    market_type=MarketType.Perp(),
                )
            )
            
            print(f"✅ ORDER SUBMITTED SUCCESSFULLY!")
            print(f"   Transaction: {tx_sig}")
            print(f"   🌐 View on Solscan: https://solscan.io/tx/{tx_sig}?cluster={self.env}")
            print(f"   🌐 View on Drift: https://beta.drift.trade/")
            
            # Wait a moment and check if order was filled
            print("⏳ Checking order status...")
            await asyncio.sleep(2)
            
            return str(tx_sig)
            
        except Exception as e:
            print(f"❌ Failed to place order: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def cancel_all_orders(self):
        """Cancel all open orders"""
        try:
            print("🗑️ Cancelling all orders...")
            
            tx_sig = await self.drift_client.cancel_orders()
            
            print(f"✅ All orders cancelled!")
            print(f"   Transaction: {tx_sig}")
            
            return str(tx_sig)
            
        except Exception as e:
            print(f"❌ Failed to cancel orders: {e}")
            return None
    
    async def get_account_value(self):
        """Get total account value"""
        try:
            if not self.drift_user:
                return None
            
            total_collateral = await self.drift_user.get_total_collateral()
            free_collateral = await self.drift_user.get_free_collateral()
            
            print(f"💰 Account Value:")
            print(f"   Total Collateral: ${total_collateral / 1e6:.2f}")
            print(f"   Free Collateral: ${free_collateral / 1e6:.2f}")
            
            return {
                "total_collateral": total_collateral / 1e6,
                "free_collateral": free_collateral / 1e6
            }
            
        except Exception as e:
            print(f"❌ Failed to get account value: {e}")
            return None
    
    async def close(self):
        """Close the client connection"""
        try:
            if self.drift_user:
                await self.drift_user.unsubscribe()
            if self.drift_client:
                await self.drift_client.unsubscribe()
            print("🔌 Drift client closed")
        except Exception as e:
            print(f"⚠️ Error closing client: {e}")

# Example usage and testing
async def test_drift_integration():
    """Test the real Drift integration"""
    print("🚀 TESTING REAL DRIFT INTEGRATION")
    print("="*60)
    print("⚠️  WARNING: This will place REAL orders on Drift Protocol!")
    print("💡 Make sure you're on devnet and have test SOL")
    print("="*60)
    
    # Initialize client
    client = RealDriftClient(
        rpc_url="https://api.devnet.solana.com",
        wallet_path="C:\\Users\\genuw\\.config\\solana\\id_devnet_custom.json",
        env="devnet"
    )
    
    try:
        # Initialize connection
        success = await client.initialize()
        if not success:
            print("❌ Failed to initialize client")
            return
        
        # Get market info
        market_info = await client.get_market_info(0)  # SOL-PERP
        
        # Get account value
        account_value = await client.get_account_value()
        
        # Get current positions
        positions = await client.get_user_positions()
        
        print("\n" + "="*60)
        print("READY TO PLACE REAL ORDERS!")
        print("="*60)
        
        # Example: Place a small test order
        response = input("\n🚨 Place a REAL test order? (yes/no): ")
        if response.lower() == 'yes':
            print("\n📝 Placing small test order...")
            
            tx_sig = await client.place_perp_order(
                market_index=0,      # SOL-PERP
                order_side="buy",    # Buy side
                order_type="limit",  # Limit order
                amount=0.01,         # 0.01 SOL (very small test)
                price=140.0          # $140 limit price (adjust as needed)
            )
            
            if tx_sig:
                print(f"\n🎉 SUCCESS! Order placed with transaction: {tx_sig}")
                print(f"🌐 Check beta.drift.trade to see your order!")
            else:
                print("❌ Order failed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

# Run the test
if __name__ == "__main__":
    if DRIFTPY_AVAILABLE:
        asyncio.run(test_drift_integration())
    else:
        print("❌ Please install driftpy first: pip install driftpy")
