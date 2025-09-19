#!/usr/bin/env python3
"""
Test Balance Calculation - Replicate bot's exact logic
"""

import asyncio
import json
import os
import sys

sys.path.append('.')

async def test_balance_calculation():
    """Test the exact same balance calculation as the bot"""
    
    print("🔍 TESTING BALANCE CALCULATION")
    print("=" * 50)
    
    try:
        # Import exactly what the bot imports
        from driftpy.drift_client import DriftClient
        from driftpy.account_subscription_config import AccountSubscriptionConfig
        from driftpy.constants.config import configs
        from solana.rpc.async_api import AsyncClient
        from anchorpy import Wallet
        from solders.keypair import Keypair
        from driftpy.constants.numeric_constants import QUOTE_PRECISION
        
        print("✅ Imports successful")
        
        # Load wallet exactly like the bot
        print("\n🔑 Loading wallet (.devnet_wallet.json)...")
        with open('.devnet_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        
        keypair = Keypair.from_bytes(bytes(wallet_data))
        print(f"   📍 Wallet Address: {keypair.pubkey()}")
        
        # RPC connection exactly like the bot  
        print("\n🌐 Connecting to RPC...")
        rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        connection = AsyncClient(rpc_url)
        
        # Test RPC connection
        try:
            # Test with a simple get_latest_blockhash call
            blockhash = await connection.get_latest_blockhash()
            print(f"   ✅ RPC Connected (latest blockhash: {str(blockhash.value.blockhash)[:10]}...)")
        except Exception as e:
            print(f"   ⚠️ RPC test failed: {e}")
            print("   Continuing anyway...")
        
        # Create DriftClient exactly like the bot
        print("\n🎯 Creating DriftClient...")
        config = configs["devnet"]
        wallet = Wallet(keypair)
        
        drift_client = DriftClient(
            connection,
            wallet,
            "devnet",
            account_subscription=AccountSubscriptionConfig("websocket")
        )
        
        print("   📡 Subscribing...")
        await drift_client.subscribe()
        await asyncio.sleep(3)  # Wait for subscription like the bot
        
        print("   ✅ Subscription complete")
        
        # Test balance calculation exactly like the bot
        print("\n💰 Testing Balance Calculation...")
        
        drift_user = drift_client.get_user()
        
        if drift_user is None:
            print("   ❌ drift_user is None")
            return
            
        print("   ✅ drift_user obtained")
        
        # Method 1: get_free_collateral (what the bot uses)
        print("\n📊 Method 1: get_free_collateral")
        try:
            free_collateral = drift_user.get_free_collateral()
            print(f"   Raw result: {free_collateral}")
            print(f"   Type: {type(free_collateral)}")
            
            if free_collateral is not None:
                # Handle different return types exactly like the bot
                if hasattr(free_collateral, 'data'):
                    collateral_value = free_collateral.data
                    print(f"   Using .data: {collateral_value}")
                elif isinstance(free_collateral, (int, float)):
                    collateral_value = free_collateral
                    print(f"   Using direct value: {collateral_value}")
                else:
                    collateral_value = float(free_collateral)
                    print(f"   Using converted value: {collateral_value}")
                
                # Convert exactly like the bot
                balance = collateral_value / QUOTE_PRECISION
                print(f"   🎯 FINAL BALANCE: {balance:.4f} SOL")
                print(f"   🔧 QUOTE_PRECISION: {QUOTE_PRECISION}")
                
                if balance > 0:
                    print("   ✅ SUCCESS: Bot should see this balance!")
                else:
                    print("   ❌ PROBLEM: Balance is zero or negative")
                    
            else:
                print("   ❌ free_collateral returned None")
                
        except Exception as e:
            print(f"   ❌ get_free_collateral failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Method 2: get_total_collateral
        print("\n📊 Method 2: get_total_collateral")
        try:
            total_collateral = drift_user.get_total_collateral()
            print(f"   Raw result: {total_collateral}")
            
            if total_collateral is not None:
                if hasattr(total_collateral, 'data'):
                    collateral_value = total_collateral.data
                else:
                    collateral_value = float(total_collateral)
                
                balance = collateral_value / QUOTE_PRECISION
                print(f"   🎯 TOTAL COLLATERAL BALANCE: {balance:.4f} SOL")
                
        except Exception as e:
            print(f"   ❌ get_total_collateral failed: {e}")
        
        # Check user account details
        print("\n👤 User Account Details:")
        try:
            user_account = drift_user.get_user_account()
            if user_account:
                print(f"   Authority: {user_account.authority}")
                print(f"   Sub Account ID: {user_account.sub_account_id}")
                
                # Check if this matches our keypair
                if str(user_account.authority) == str(keypair.pubkey()):
                    print("   ✅ Authority matches our keypair")
                else:
                    print("   ❌ Authority MISMATCH with our keypair!")
                    print(f"      Expected: {keypair.pubkey()}")
                    print(f"      Got: {user_account.authority}")
                
                # Check spot positions
                print("   Spot Positions:")
                for i, pos in enumerate(user_account.spot_positions):
                    if pos.market_index == 0 and abs(pos.scaled_balance) > 0:  # USDC
                        print(f"      Market {pos.market_index}: {pos.scaled_balance}")
                        
        except Exception as e:
            print(f"   ❌ User account check failed: {e}")
        
        # Cleanup
        await drift_client.unsubscribe()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_balance_calculation())
