#!/usr/bin/env python3
"""
Check balance of specific funded wallet address
"""

import asyncio
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

async def check_wallet_balance(wallet_address: str):
    """Check SOL balance of specific wallet"""
    print(f"🔍 Checking balance for wallet: {wallet_address}")
    print("=" * 60)
    
    # Connect to Solana devnet
    rpc_url = "https://api.devnet.solana.com"
    print(f"🌐 Connecting to: {rpc_url}")
    
    async with AsyncClient(rpc_url) as client:
        try:
            # Convert string to Pubkey
            pubkey = Pubkey.from_string(wallet_address)
            
            # Get balance
            balance_response = await client.get_balance(pubkey)
            balance_lamports = balance_response.value
            balance_sol = balance_lamports / 1e9
            
            print(f"✅ Balance Check Results:")
            print(f"   Wallet: {wallet_address}")
            print(f"   SOL Balance: {balance_sol:.6f} SOL")
            print(f"   Lamports: {balance_lamports:,}")
            
            # Estimate USD value (approximate SOL price)
            sol_price = 195.48  # Approximate current price
            balance_usd = balance_sol * sol_price
            print(f"   USD Value: ~${balance_usd:.2f}")
            
            if balance_sol > 0.01:
                print(f"🎯 SUFFICIENT BALANCE FOR TRADING!")
                print(f"💡 This wallet can be used with your Drift bot!")
            else:
                print(f"⚠️  LOW BALANCE - May not be sufficient for trading")
                
        except Exception as e:
            print(f"❌ Error checking balance: {e}")
            
        # Get recent transactions
        print(f"\n📊 Checking recent transactions...")
        try:
            signatures = await client.get_signatures_for_address(pubkey, limit=5)
            if signatures.value:
                print(f"✅ Found {len(signatures.value)} recent transactions:")
                for sig in signatures.value[:3]:  # Show first 3
                    print(f"   📝 {sig.signature[:8]}...{sig.signature[-8:]}")
            else:
                print("ℹ️  No recent transactions found")
        except Exception as e:
            print(f"⚠️  Could not fetch transactions: {e}")

if __name__ == "__main__":
    # The funded wallet address from your Drift UI
    FUNDED_WALLET = "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
    
    print("🧪 WALLET BALANCE CHECKER")
    print("=" * 60)
    print(f"Target Wallet: {FUNDED_WALLET}")
    print(f"Expected Balance: ~$607.52 (from your Drift UI)")
    print("=" * 60)
    
    asyncio.run(check_wallet_balance(FUNDED_WALLET))
    
    print("\n" + "=" * 60)
    print("💡 NEXT STEPS:")
    print("1. Verify this wallet shows $607.52 in your Drift UI")
    print("2. Export the private key from Drift UI or browser wallet")
    print("3. Save it as 'funded_wallet.json'")
    print("4. Update your bot to use this funded wallet!")
    print("=" * 60)
