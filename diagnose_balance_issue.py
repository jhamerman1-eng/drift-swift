#!/usr/bin/env python3
"""
CRITICAL BALANCE DIAGNOSIS
Check why bot shows 0.0000 SOL when UI shows $795.02 available
"""

import asyncio
import logging
import sys
import os
import json
from pathlib import Path

# Add required imports
sys.path.append('.')
sys.path.append('scripts/bots')

try:
    from driftpy.drift_client import DriftClient
    from driftpy.account_subscription_config import AccountSubscriptionConfig
    from driftpy.constants.config import configs
    from solana.rpc.async_api import AsyncClient
    from anchorpy import Wallet
    from solders.keypair import Keypair
    from driftpy.constants.numeric_constants import QUOTE_PRECISION
    print("✅ DriftPy imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

async def diagnose_balance_issue():
    """Comprehensive balance diagnosis"""
    print("🔍 COMPREHENSIVE BALANCE DIAGNOSIS")
    print("=" * 60)
    
    # Step 1: Check environment configuration
    print("\n📋 STEP 1: Environment Configuration")
    drift_env = os.getenv('DRIFT_ENV', 'devnet')
    rpc_url = os.getenv('RPC_OVERRIDE_URL', 'https://devnet.helius-rpc.com/?api-key=YOUR_KEY')
    
    print(f"   Environment: {drift_env}")
    print(f"   RPC URL: {rpc_url[:50]}...")
    
    # Step 2: Check keypair
    print("\n🔑 STEP 2: Keypair Analysis")
    try:
        # Try loading from different possible locations
        keypair_paths = [
            "configs/keypair.json",
            "keypair.json", 
            os.path.expanduser("~/.config/solana/id.json")
        ]
        
        keypair = None
        keypair_path = None
        
        for path in keypair_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    secret_key = json.load(f)
                keypair = Keypair.from_bytes(bytes(secret_key))
                keypair_path = path
                break
        
        if keypair:
            print(f"   ✅ Keypair loaded from: {keypair_path}")
            print(f"   📍 Public Key: {keypair.pubkey()}")
        else:
            print("   ❌ No keypair found in standard locations")
            return
            
    except Exception as e:
        print(f"   ❌ Keypair loading failed: {e}")
        return
    
    # Step 3: Test RPC connection
    print("\n🌐 STEP 3: RPC Connection Test")
    try:
        connection = AsyncClient(rpc_url)
        
        # Test basic RPC call
        health = await connection.get_health()
        print(f"   ✅ RPC Health: {health}")
        
        # Check wallet SOL balance directly
        balance_response = await connection.get_balance(keypair.pubkey())
        if balance_response.value is not None:
            sol_balance = balance_response.value / 1e9
            print(f"   💰 Wallet SOL Balance: {sol_balance:.4f} SOL")
        else:
            print("   ❌ Failed to get wallet balance")
            
    except Exception as e:
        print(f"   ❌ RPC connection failed: {e}")
        return
    
    # Step 4: Test DriftClient initialization
    print("\n🎯 STEP 4: DriftClient Analysis")
    try:
        # Initialize DriftClient the same way as the bot
        config = configs[drift_env]
        wallet = Wallet(keypair)
        
        print(f"   📊 Drift Config: {config}")
        print(f"   🔗 Program ID: {config.drift_program_id}")
        
        # Create client with subscription
        drift_client = DriftClient(
            connection,
            wallet,
            drift_env,
            account_subscription=AccountSubscriptionConfig("websocket")
        )
        
        print("   ✅ DriftClient created")
        
        # Subscribe and wait
        print("   🔄 Subscribing to Drift...")
        await drift_client.subscribe()
        await asyncio.sleep(2)  # Wait for subscription
        
        print("   ✅ Subscription complete")
        
    except Exception as e:
        print(f"   ❌ DriftClient initialization failed: {e}")
        return
    
    # Step 5: Test balance methods
    print("\n💰 STEP 5: Balance Method Testing")
    try:
        drift_user = drift_client.get_user()
        
        if drift_user is None:
            print("   ❌ drift_user is None")
            return
        
        print("   ✅ drift_user obtained")
        
        # Test free collateral
        try:
            free_collateral = drift_user.get_free_collateral()
            print(f"   📊 Raw free_collateral: {free_collateral}")
            print(f"   📊 free_collateral type: {type(free_collateral)}")
            
            if free_collateral is not None:
                # Handle different return types
                if hasattr(free_collateral, 'data'):
                    collateral_value = free_collateral.data
                    print(f"   📊 collateral_value (from .data): {collateral_value}")
                elif isinstance(free_collateral, (int, float)):
                    collateral_value = free_collateral
                    print(f"   📊 collateral_value (direct): {collateral_value}")
                else:
                    collateral_value = float(free_collateral)
                    print(f"   📊 collateral_value (converted): {collateral_value}")
                
                # Convert to SOL
                balance_sol = collateral_value / QUOTE_PRECISION
                print(f"   💰 Free Collateral (SOL): {balance_sol:.4f}")
                print(f"   📏 QUOTE_PRECISION: {QUOTE_PRECISION}")
                
            else:
                print("   ⚠️  free_collateral is None")
                
        except Exception as e:
            print(f"   ❌ free_collateral test failed: {e}")
        
        # Test total collateral
        try:
            total_collateral = drift_user.get_total_collateral()
            print(f"   📊 Raw total_collateral: {total_collateral}")
            
            if total_collateral is not None:
                if hasattr(total_collateral, 'data'):
                    collateral_value = total_collateral.data
                else:
                    collateral_value = float(total_collateral)
                
                balance_sol = collateral_value / QUOTE_PRECISION
                print(f"   💰 Total Collateral (SOL): {balance_sol:.4f}")
            else:
                print("   ⚠️  total_collateral is None")
                
        except Exception as e:
            print(f"   ❌ total_collateral test failed: {e}")
        
        # Test account info
        try:
            user_account = drift_user.get_user_account()
            print(f"   📊 User account: {user_account}")
            
            if user_account:
                print(f"   📊 User account authority: {user_account.authority}")
                print(f"   📊 User account sub_account_id: {user_account.sub_account_id}")
                
                # Check spot positions for USDC
                if hasattr(user_account, 'spot_positions'):
                    for i, pos in enumerate(user_account.spot_positions):
                        if pos.market_index == 0 and pos.scaled_balance != 0:  # USDC market
                            print(f"   💵 USDC Position {i}: {pos.scaled_balance}")
                            
        except Exception as e:
            print(f"   ❌ user_account test failed: {e}")
            
    except Exception as e:
        print(f"   ❌ Balance method testing failed: {e}")
    
    # Step 6: Comparison with UI values
    print("\n🎯 STEP 6: UI Comparison")
    print("   🖥️  UI Shows: $795.02 available, 3.09354 SOL")
    print("   🤖 Bot Shows: 0.0000 SOL (WRONG)")
    print("   💡 Expected: Bot should show ~3.0 SOL or equivalent USDC")
    
    # Cleanup
    try:
        await drift_client.unsubscribe()
        print("\n✅ Cleanup complete")
    except:
        pass

if __name__ == "__main__":
    asyncio.run(diagnose_balance_issue())


