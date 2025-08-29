#!/usr/bin/env python3
"""
Test the funded wallet keypair
"""

import asyncio
import json
import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient

async def test_funded_keypair():
    """Test the funded wallet keypair"""
    print("🧪 TESTING FUNDED WALLET KEYPAIR")
    print("=" * 60)
    
    # Load the private key
    keypair_file = "funded_wallet.json"
    target_address = "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
    
    try:
        with open(keypair_file, 'r') as f:
            private_key_base58 = f.read().strip()
        
        print(f"🔑 Loaded private key from: {keypair_file}")
        print(f"📏 Private key length: {len(private_key_base58)} characters")
        
        # Decode base58 private key
        private_key_bytes = base58.b58decode(private_key_base58)
        print(f"📏 Decoded bytes length: {len(private_key_bytes)} bytes")
        
        # Create keypair
        if len(private_key_bytes) == 64:
            # 64-byte private key
            keypair = Keypair.from_bytes(private_key_bytes)
            print("✅ Created keypair from 64-byte private key")
        else:
            # Try 32-byte seed method
            keypair = Keypair.from_seed(private_key_bytes[:32])
            print("✅ Created keypair from 32-byte seed")
        
        # Get public key
        public_key = str(keypair.pubkey())
        print(f"🔑 Public Key: {public_key}")
        
        # Verify it matches the target
        if public_key == target_address:
            print("🎯 SUCCESS! Keypair matches your funded wallet!")
        else:
            print(f"❌ MISMATCH! Expected: {target_address}")
            print(f"   Got: {public_key}")
            return False
        
        # Test wallet balance
        print(f"\n💰 Testing wallet balance...")
        rpc_url = "https://api.devnet.solana.com"
        
        async with AsyncClient(rpc_url) as client:
            try:
                balance_response = await client.get_balance(Pubkey.from_string(public_key))
                balance_lamports = balance_response.value
                balance_sol = balance_lamports / 1e9
                
                print(f"✅ Balance Check:")
                print(f"   SOL: {balance_sol:.6f} SOL")
                print(f"   Lamports: {balance_lamports:,}")
                
                sol_price = 195.48
                balance_usd = balance_sol * sol_price
                print(f"   USD: ~${balance_usd:.2f}")
                
                if balance_sol > 0.01:
                    print(f"🎯 SUFFICIENT BALANCE FOR TRADING!")
                else:
                    print(f"⚠️  LOW BALANCE")
                    
            except Exception as e:
                print(f"❌ Balance check failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing keypair: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_funded_keypair())
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 FUNDED WALLET KEYPAIR VERIFIED!")
        print("💡 You can now use this with your Drift bot!")
        print("🚀 Ready to place real orders on Drift devnet!")
    else:
        print("❌ KEYPAIR TEST FAILED")
        print("💡 Check the private key format")
    print("=" * 60)
