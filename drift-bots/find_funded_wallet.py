#!/usr/bin/env python3
"""
Find which keypair file corresponds to the funded wallet
"""

import asyncio
import json
import os
from solders.keypair import Keypair
from solders.pubkey import Pubkey

async def check_keypair_file(file_path: str, target_address: str):
    """Check if a keypair file corresponds to the target wallet address"""
    try:
        with open(file_path, 'r') as f:
            data = f.read().strip()
        
        # Parse keypair data
        if data.startswith('[') and data.endswith(']'):
            keypair_data = json.loads(data)
            print(f"📏 {file_path}: {len(keypair_data)} bytes")
            
            if len(keypair_data) == 32:
                # 32-byte key - try seed method
                try:
                    keypair = Keypair.from_seed(keypair_data)
                    address = str(keypair.pubkey())
                    print(f"   🔑 32-byte key (seed method): {address}")
                    if address == target_address:
                        print(f"   🎯 MATCH FOUND! This is your funded wallet!")
                        return True
                except Exception as e:
                    print(f"   ❌ Seed method failed: {e}")
                    
            elif len(keypair_data) == 64:
                # 64-byte key - try bytes method
                try:
                    keypair = Keypair.from_bytes(keypair_data)
                    address = str(keypair.pubkey())
                    print(f"   🔑 64-byte key: {address}")
                    if address == target_address:
                        print(f"   🎯 MATCH FOUND! This is your funded wallet!")
                        return True
                except Exception as e:
                    print(f"   ❌ Bytes method failed: {e}")
            else:
                print(f"   ⚠️  Unexpected length: {len(keypair_data)}")
                
        else:
            print(f"   ⚠️  Not a JSON array format")
            
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")
    
    return False

async def find_funded_wallet():
    """Find which keypair file contains the funded wallet"""
    target_address = "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
    
    print("🔍 FINDING YOUR FUNDED WALLET KEYPAIR")
    print("=" * 60)
    print(f"Target Address: {target_address}")
    print(f"Expected Balance: ~1.057 SOL (~$206)")
    print("=" * 60)
    
    # List of keypair files to check
    keypair_files = [
        "working_keypair.json",
        "test_keypair.json", 
        "real_test_keypair.json",
        "auto_generated_keypair.json"
    ]
    
    found_wallet = False
    
    for file_path in keypair_files:
        if os.path.exists(file_path):
            print(f"\n🔍 Checking: {file_path}")
            if await check_keypair_file(file_path, target_address):
                found_wallet = True
                print(f"\n🎉 SUCCESS! Your funded wallet is in: {file_path}")
                print(f"💡 You can now use this file with your Drift bot!")
                break
        else:
            print(f"\n❌ File not found: {file_path}")
    
    if not found_wallet:
        print(f"\n❌ FUNDED WALLET NOT FOUND IN ANY KEYPAIR FILES")
        print(f"💡 You need to export the private key from your Drift UI")
        print(f"💡 Or from your browser wallet extension")
        print(f"💡 Target wallet: {target_address}")
    
    print("\n" + "=" * 60)
    print("💡 NEXT STEPS:")
    if found_wallet:
        print("1. ✅ Funded wallet found!")
        print("2. 🚀 Update your bot to use this keypair file")
        print("3. 🎯 Start placing real orders on Drift!")
    else:
        print("1. 🔑 Export private key from Drift UI")
        print("2. 💾 Save as 'funded_wallet.json'")
        print("3. 🚀 Update your bot configuration")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(find_funded_wallet())
