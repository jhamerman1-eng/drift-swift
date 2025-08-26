#!/usr/bin/env python3
"""
Fixed Drift Trading Integration - Uses Real Funded Wallet + Live Markets
Addresses the keypair issue and connects to actual Drift devnet markets
"""

import asyncio
import json
import os
import base58
from typing import Optional, Dict, Any
from dataclasses import dataclass
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from anchorpy import Wallet

# DriftPy imports
try:
    from driftpy.drift_client import DriftClient
    from driftpy.types import OrderParams, OrderType, PositionDirection, MarketType, PostOnlyParams
    from driftpy.accounts import get_perp_market_account
    DRIFTPY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  DriftPy import error: {e}")
    DRIFTPY_AVAILABLE = False

@dataclass
class WalletInfo:
    """Wallet information and balance"""
    public_key: str
    balance_sol: float
    balance_usd: float
    keypair_path: str

class FixedDriftClient:
    """Fixed Drift client that uses your actual funded wallet"""
    
    def __init__(self, funded_keypair_path: str):
        self.funded_keypair_path = funded_keypair_path
        self.connection: Optional[AsyncClient] = None
        self.drift_client: Optional[DriftClient] = None
        self.wallet: Optional[Wallet] = None
        self.wallet_info: Optional[WalletInfo] = None
        
        # Use REAL Drift devnet endpoints
        self.rpc_url = "https://api.devnet.solana.com"  # Official Solana devnet
        self.drift_program_id = "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"
        
    async def initialize(self):
        """Initialize with your real funded wallet"""
        print("🔧 FIXING WALLET CONNECTION...")
        print("="*50)
        
        # 1. Load your ACTUAL funded wallet
        await self._load_funded_wallet()
        
        # 2. Connect to Solana devnet
        await self._connect_to_solana()
        
        # 3. Verify wallet has funds
        await self._verify_wallet_funds()
        
        # 4. Initialize Drift client with your wallet
        await self._initialize_drift_client()
        
        # 5. Connect to live Drift markets
        await self._connect_to_drift_markets()
        
        print("🚀 FIXED: Now using your real funded wallet!")
        
    async def _load_funded_wallet(self):
        """Load your actual funded wallet (no more auto-generation!)"""
        print(f"🔑 Loading your funded wallet from: {self.funded_keypair_path}")
        
        if not os.path.exists(self.funded_keypair_path):
            raise FileNotFoundError(f"❌ Funded wallet not found: {self.funded_keypair_path}")
        
        try:
            # Load the keypair data
            with open(self.funded_keypair_path, 'r') as f:
                data = f.read().strip()
            
            # Handle different keypair formats
            if data.startswith('[') and data.endswith(']'):
                # JSON array format [1,2,3,...]
                keypair_data = json.loads(data)
                print(f"📏 Keypair data length: {len(keypair_data)} bytes")
                
                if len(keypair_data) == 32:
                    # 32-byte secret key - use seed method
                    print("🔑 Using 32-byte key with seed method")
                    solana_keypair = Keypair.from_seed(keypair_data)
                elif len(keypair_data) == 64:
                    # 64-byte secret key - use bytes method
                    print("🔑 Using 64-byte key with bytes method")
                    keypair_bytes = bytes(keypair_data)
                    solana_keypair = Keypair.from_bytes(keypair_bytes)
                else:
                    raise ValueError(f"Invalid keypair length: {len(keypair_data)}")
                
            elif len(data) == 88 or len(data) == 128:
                # Base58 format
                print("🔑 Using base58 format")
                keypair_bytes = base58.b58decode(data)
                solana_keypair = Keypair.from_secret_key(keypair_bytes)
                
            else:
                raise ValueError("Unrecognized keypair format")
            
            # Wrap in anchorpy Wallet for DriftPy
            self.wallet = Wallet(solana_keypair)
            
            public_key = str(self.wallet.public_key)
            print(f"✅ Loaded funded wallet: {public_key}")
            
            return public_key
            
        except Exception as e:
            print(f"❌ Failed to load funded wallet: {e}")
            print("💡 Make sure your keypair file contains the correct format:")
            print("   - JSON array: [1,2,3,...] (64 numbers)")
            print("   - Base58 string: Your private key as base58")
            raise
    
    async def _connect_to_solana(self):
        """Connect to Solana devnet with proper endpoint"""
        print(f"🌐 Connecting to Solana devnet: {self.rpc_url}")
        
        self.connection = AsyncClient(self.rpc_url)
        
        # Test connection
        try:
            slot = await self.connection.get_slot()
            print(f"✅ Connected to Solana devnet (slot: {slot.value})")
        except Exception as e:
            print(f"❌ Solana connection failed: {e}")
            raise
    
    async def _verify_wallet_funds(self):
        """Verify your wallet has the expected funds"""
        print("💰 Checking your wallet balance...")
        
        try:
            # Get SOL balance
            balance_response = await self.connection.get_balance(self.wallet.public_key)
            balance_lamports = balance_response.value
            balance_sol = balance_lamports / 1e9
            
            # Estimate USD value (approximate)
            sol_price = 195.48  # From your Drift UI
            balance_usd = balance_sol * sol_price
            
            self.wallet_info = WalletInfo(
                public_key=str(self.wallet.public_key),
                balance_sol=balance_sol,
                balance_usd=balance_usd,
                keypair_path=self.funded_keypair_path
            )
            
            print(f"✅ Wallet Balance:")
            print(f"   Public Key: {self.wallet_info.public_key}")
            print(f"   SOL Balance: {balance_sol:.4f} SOL")
            print(f"   USD Value: ~${balance_usd:.2f}")
            
            if balance_sol < 0.01:
                print("⚠️  WARNING: Low SOL balance for trading and fees")
            else:
                print("🎯 Sufficient balance for trading!")
                
        except Exception as e:
            print(f"❌ Balance check failed: {e}")
            raise
    
    async def _initialize_drift_client(self):
        """Initialize DriftPy client with your funded wallet"""
        if not DRIFTPY_AVAILABLE:
            raise RuntimeError("DriftPy not available - run: pip install driftpy")
        
        print("📡 Initializing Drift client with your funded wallet...")
        
        try:
            # Create DriftClient with your wallet
            self.drift_client = DriftClient(
                connection=self.connection,
                wallet=self.wallet,
                env="devnet"  # Use devnet environment
            )
            
            print("✅ DriftClient created with your funded wallet")
            
            # Initialize user account (required for trading)
            print("👤 Setting up user account...")
            
            try:
                # Try to add/initialize user account
                await self.drift_client.add_user(0)  # Sub-account 0
                print("✅ User account initialized")
            except Exception as user_error:
                print(f"ℹ️  User account: {user_error}")
                # May already exist, continue
            
            # Subscribe to market data
            print("📊 Subscribing to Drift market data...")
            await self.drift_client.subscribe()
            print("✅ Subscribed to Drift protocol")
            
        except Exception as e:
            print(f"❌ DriftClient initialization failed: {e}")
            raise
    
    async def _connect_to_drift_markets(self):
        """Connect to live Drift devnet markets"""
        print("🏪 Connecting to live Drift markets...")
        
        try:
            # Get SOL-PERP market (market index 0)
            market_pubkey = self.drift_client.get_perp_market_public_key(0)
            print(f"📊 SOL-PERP market pubkey: {market_pubkey}")
            
            # Get market account data
            market_account = await get_perp_market_account(self.connection, market_pubkey)
            print("✅ Connected to SOL-PERP market")
            
            # Get oracle price (this is the REAL price)
            oracle_data = self.drift_client.get_oracle_price_data_for_perp_market(0)
            oracle_price = self.drift_client.convert_to_number(oracle_data.price)
            
            print(f"🎯 LIVE SOL-PERP Price: ${oracle_price:.3f}")
            print("✅ Connected to live Drift markets!")
            
        except Exception as e:
            print(f"❌ Market connection failed: {e}")
            # Continue - we can still trade even if market data fetch fails
            print("ℹ️  Will use alternative price feeds")
    
    async def get_live_price(self, market_index: int = 0) -> float:
        """Get REAL live price from Drift oracle"""
        try:
            oracle_data = self.drift_client.get_oracle_price_data_for_perp_market(market_index)
            price = self.drift_client.convert_to_number(oracle_data.price)
            print(f"📈 Live Oracle Price: ${price:.3f}")
            return price
        except Exception as e:
            print(f"⚠️  Oracle price failed: {e}, using fallback")
            return 195.48  # Fallback to your UI price
    
    async def place_real_order(self, side: str, size_usd: float, price: Optional[float] = None) -> str:
        """Place REAL order on Drift devnet that will show on beta.drift.trade"""
        print("🚀 PLACING REAL ORDER ON DRIFT DEVNET")
        print("="*50)
        print(f"💰 Using your funded wallet: {self.wallet_info.public_key}")
        print(f"💳 Balance: {self.wallet_info.balance_sol:.4f} SOL (${self.wallet_info.balance_usd:.2f})")
        
        try:
            # Get live price if not specified
            if not price:
                price = await self.get_live_price()
            
            # Calculate SOL amount
            sol_amount = size_usd / price
            
            print(f"📊 Order Details:")
            print(f"   Side: {side.upper()}")
            print(f"   Size: {sol_amount:.4f} SOL (${size_usd:.2f})")
            print(f"   Price: ${price:.3f}")
            print(f"   Market: SOL-PERP (devnet)")
            
            # Create order parameters
            direction = PositionDirection.Long() if side.lower() == 'buy' else PositionDirection.Short()
            
            order_params = OrderParams(
                order_type=OrderType.Limit(),
                base_asset_amount=self.drift_client.convert_to_perp_precision(sol_amount),
                market_index=0,  # SOL-PERP
                direction=direction,
                price=self.drift_client.convert_to_price_precision(price),
                market_type=MarketType.Perp(),
                post_only=PostOnlyParams.TryPostOnly()  # Maker order
            )
            
            print("📝 Created OrderParams with proper precision")
            
            # Place the order via DriftPy
            print("🚀 Broadcasting to Drift devnet...")
            
            signature = await self.drift_client.place_perp_order(order_params)
            
            print("✅ REAL ORDER PLACED ON DRIFT!")
            print(f"🔗 Transaction: {signature}")
            print(f"🌐 View on beta.drift.trade (devnet)")
            print(f"🔍 Solscan: https://devnet.solscan.io/tx/{signature}")
            
            return str(signature)
            
        except Exception as e:
            print(f"❌ Real order placement failed: {e}")
            print("💡 This may be due to:")
            print("   - Insufficient balance for margin requirements")
            print("   - Network issues")
            print("   - Invalid order parameters")
            raise
    
    async def get_real_positions(self) -> Dict[str, Any]:
        """Get your REAL positions from Drift"""
        try:
            user = self.drift_client.get_user()
            if not user:
                return {}
            
            positions = {}
            perp_positions = user.get_perp_positions()
            
            for position in perp_positions:
                if position.base_asset_amount != 0:
                    size = self.drift_client.convert_to_number(position.base_asset_amount)
                    
                    positions[f"market_{position.market_index}"] = {
                        'market_index': position.market_index,
                        'size': size,
                        'side': 'long' if size > 0 else 'short'
                    }
            
            return positions
            
        except Exception as e:
            print(f"❌ Position fetch failed: {e}")
            return {}
    
    async def close(self):
        """Cleanup connections"""
        if self.drift_client:
            try:
                await self.drift_client.unsubscribe()
            except:
                pass
        
        if self.connection:
            await self.connection.close()
        
        print("🔒 Drift client closed")

# Easy integration function for your existing code
async def create_fixed_drift_client(funded_keypair_path: str) -> FixedDriftClient:
    """Create properly configured Drift client with your funded wallet"""
    client = FixedDriftClient(funded_keypair_path)
    await client.initialize()
    return client

# Test function to verify everything works
async def test_fixed_wallet_integration():
    """Test the fixed wallet integration"""
    print("🧪 TESTING FIXED WALLET INTEGRATION")
    print("="*50)
    
    # IMPORTANT: Update this path to your actual funded wallet
    # Replace with the path to your wallet that has $607.52
    FUNDED_KEYPAIR_PATH = "working_keypair.json"  # UPDATE THIS!
    
    if not os.path.exists(FUNDED_KEYPAIR_PATH):
        print("❌ Please update FUNDED_KEYPAIR_PATH to your actual funded wallet")
        print("💡 This should be the wallet showing $607.52 in your Drift UI")
        return
    
    try:
        # Create client with your funded wallet
        client = await create_fixed_drift_client(FUNDED_KEYPAIR_PATH)
        
        # Test 1: Verify wallet funds
        print(f"✅ Using funded wallet: {client.wallet_info.public_key}")
        print(f"💰 Balance: {client.wallet_info.balance_sol:.4f} SOL (${client.wallet_info.balance_usd:.2f})")
        
        # Test 2: Get live price
        live_price = await client.get_live_price()
        print(f"📈 Live SOL price: ${live_price:.3f}")
        
        # Test 3: Check positions
        positions = await client.get_real_positions()
        print(f"📊 Current positions: {len(positions)}")
        
        # Test 4: Place small test order (optional - uncomment to trade)
        """
        print("🚀 Placing test order...")
        signature = await client.place_real_order("buy", 5.0)  # $5 test order
        print(f"✅ Test order placed: {signature}")
        """
        
        await client.close()
        
        print("🎉 FIXED WALLET INTEGRATION WORKING!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

# Drop-in replacement for your existing build_client_from_config
async def build_client_from_config_fixed(config_path: str) -> FixedDriftClient:
    """Fixed version that uses your funded wallet from config"""
    import yaml
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get keypair path from config
    keypair_path = config.get('wallets', {}).get('maker_keypair_path')
    if not keypair_path:
        keypair_path = os.getenv('KEYPAIR_PATH')
    
    if not keypair_path:
        raise ValueError("No keypair path found in config or KEYPAIR_PATH env var")
    
    # Expand environment variables
    keypair_path = os.path.expandvars(keypair_path)
    
    print(f"🔧 FIXED: Using keypair from config: {keypair_path}")
    
    return await create_fixed_drift_client(keypair_path)

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_fixed_wallet_integration())
