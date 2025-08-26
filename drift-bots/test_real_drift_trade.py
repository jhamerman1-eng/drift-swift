#!/usr/bin/env python3
"""
TEST REAL DRIFT TRADE - Place a single real order on beta.drift.trade
"""
import asyncio
import os
from libs.drift.client import Order, OrderSide

async def test_single_real_trade():
    """Test placing a single real trade on Drift"""
    print("🚀 TESTING SINGLE REAL TRADE ON BETA.DRIFT.TRADE")
    print("="*60)
    
    # Configuration
    rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
    wallet_path = r"C:\Users\genuw\.config\solana\id_devnet_custom.json"
    market = "SOL-PERP"
    
    print(f"📋 Configuration:")
    print(f"   Market: {market}")
    print(f"   RPC: {rpc_url}")
    print(f"   Wallet: {wallet_path}")
    print(f"   Network: Devnet (beta.drift.trade)")
    
    try:
        # Import and test DriftPy
        print(f"\n🔍 Testing DriftPy availability...")
        from driftpy import keypair, types, drift_client
        print(f"✅ DriftPy modules loaded successfully!")
        print(f"   Version: {driftpy.__version__}")
        
        # Test wallet loading
        print(f"\n🔑 Testing wallet loading...")
        with open(wallet_path, 'r') as f:
            keypair_data = json.load(f)
        
        # Create keypair
        kp = keypair.Keypair.from_bytes(keypair_data)
        print(f"✅ Wallet loaded: {kp.public_key}")
        
        # Test Solana connection
        print(f"\n📡 Testing Solana connection...")
        from solana.rpc.async_api import AsyncClient
        solana_client = AsyncClient(rpc_url)
        
        # Get balance
        balance_response = await solana_client.get_balance(kp.public_key)
        if balance_response.value:
            balance_sol = balance_response.value / 1e9
            print(f"✅ Balance: {balance_sol:.4f} SOL")
            
            if balance_sol < 0.1:
                print(f"⚠️  Balance low! Need at least 0.1 SOL for gas")
                print(f"💡 Run: solana airdrop 2 {kp.public_key} --url {rpc_url}")
                return False
        else:
            print(f"❌ Failed to get balance")
            return False
        
        # Initialize Drift client
        print(f"\n🚀 Initializing Drift client...")
        drift_client_instance = drift_client.DriftClient(
            connection=solana_client,
            wallet=kp,
            env='devnet'
        )
        
        # Subscribe to Drift state
        print(f"📡 Subscribing to Drift state...")
        await drift_client_instance.subscribe()
        print(f"✅ Drift client ready!")
        
        # Create test order
        print(f"\n📝 Creating test order...")
        test_order = Order(
            side=OrderSide.BUY,
            price=149.50,
            size_usd=25.0
        )
        
        print(f"   Side: {test_order.side.value.upper()}")
        print(f"   Size: ${test_order.size_usd}")
        print(f"   Price: ${test_order.price}")
        print(f"   Market: {market}")
        
        # Place real order
        print(f"\n🚀 PLACING REAL ORDER ON DRIFT!")
        print(f"🌐 This will appear on beta.drift.trade!")
        
        # Import DriftPy types
        from driftpy.types import PositionDirection, OrderType, OrderParams, PostOnlyParams
        
        # Create order parameters
        order_params = OrderParams(
            order_type=OrderType.Limit,
            base_asset_amount=int(test_order.size_usd * 1000000),  # Convert to base units
            market_index=0,  # SOL-PERP market index
            direction=PositionDirection.Long,
            market_type=0,  # Perp market
            price=int(test_order.price * 1000000),  # Convert to base units
            post_only=PostOnlyParams.MustPostOnly
        )
        
        # Submit order
        result = await drift_client_instance.place_perp_order(order_params)
        
        if hasattr(result, 'success') and result.success:
            tx_sig = result.tx_sig
            print(f"\n🎉 SUCCESS! REAL ORDER PLACED ON DRIFT!")
            print(f"   Transaction: {tx_sig}")
            print(f"   🌐 Check beta.drift.trade NOW!")
            print(f"   🔗 Explorer: https://explorer.solana.com/tx/{tx_sig}?cluster=devnet")
            return True
        else:
            error_msg = getattr(result, 'error', 'Unknown error')
            print(f"\n❌ Order failed: {error_msg}")
            return False
            
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print(f"💡 Install dependencies: pip install driftpy solana")
        return False
    except FileNotFoundError:
        print(f"\n❌ Wallet file not found: {wallet_path}")
        print(f"💡 Check your wallet path configuration")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"💡 Check the error details above")
        return False
    finally:
        # Cleanup
        try:
            if 'solana_client' in locals():
                await solana_client.close()
        except:
            pass

async def main():
    """Main function"""
    print("🔥 SINGLE REAL DRIFT TRADE TEST")
    print("="*60)
    print("This will place a REAL order on beta.drift.trade!")
    print("="*60)
    
    success = await test_single_real_trade()
    
    print(f"\n{'='*60}")
    print(f"📊 TEST RESULT: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"{'='*60}")
    
    if success:
        print(f"🎉 Real Drift trading is working!")
        print(f"🌐 Your order is now on beta.drift.trade!")
        print(f"💡 You can now place real trades!")
    else:
        print(f"❌ Real Drift trading failed")
        print(f"💡 Check the error messages above")
        print(f"🔧 Common fixes:")
        print(f"   1. Install dependencies: pip install driftpy solana")
        print(f"   2. Check wallet path and balance")
        print(f"   3. Verify RPC endpoint is accessible")

if __name__ == "__main__":
    import json
    import driftpy
    asyncio.run(main())
