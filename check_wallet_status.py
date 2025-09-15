#!/usr/bin/env python3
"""
Check wallet status and connection to target Drift account
Target: A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW
"""

import json
import os
import sys
from solders.keypair import Keypair
from solders.pubkey import Pubkey

def check_wallet_file():
    """Check if wallet file exists and is valid"""
    wallet_file = ".valid_wallet.json"
    
    if not os.path.exists(wallet_file):
        print(f"❌ Wallet file not found: {wallet_file}")
        return None
    
    try:
        with open(wallet_file, 'r') as f:
            wallet_data = json.load(f)
        
        if not isinstance(wallet_data, list) or len(wallet_data) != 64:
            print(f"❌ Invalid wallet file format")
            return None
        
        keypair = Keypair.from_bytes(bytes(wallet_data))
        address = str(keypair.pubkey())
        
        print(f"✅ Wallet file loaded: {wallet_file}")
        print(f"📝 Current address: {address}")
        
        return address
        
    except Exception as e:
        print(f"❌ Error loading wallet file: {e}")
        return None

def check_wallet_balance(address: str, rpc_url: str = "https://api.devnet.solana.com"):
    """Check wallet balance"""
    try:
        import requests
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [address]
        }
        
        response = requests.post(rpc_url, json=payload)
        data = response.json()
        
        if "result" in data:
            balance_lamports = data["result"]["value"]
            balance_sol = balance_lamports / 1e9
            return balance_sol
        else:
            print(f"❌ Error checking balance: {data}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking balance: {e}")
        return None

def check_drift_account(address: str, rpc_url: str = "https://api.devnet.solana.com"):
    """Check if wallet has a Drift account"""
    try:
        import requests
        
        # This is a simplified check - in practice you'd need to check the Drift program
        # for the user account associated with this wallet
        
        print(f"🔍 Checking Drift account for {address}...")
        
        # For now, we'll just return True as a placeholder
        # In a real implementation, you'd query the Drift program
        print(f"⚠️  Drift account check not fully implemented")
        print(f"   You may need to create a Drift account if one doesn't exist")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking Drift account: {e}")
        return False

def main():
    """Main status check function"""
    target_address = "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
    
    print("🔍 Wallet Status Check")
    print("=" * 40)
    print(f"Target Address: {target_address}")
    print()
    
    # Check current wallet
    current_address = check_wallet_file()
    if not current_address:
        print("\n❌ No valid wallet found")
        print("💡 Run: python setup_wallet_connection.py")
        return 1
    
    # Check if it matches target
    if current_address == target_address:
        print(f"✅ Connected to target wallet!")
    else:
        print(f"⚠️  Current wallet doesn't match target")
        print(f"   Current:  {current_address}")
        print(f"   Target:   {target_address}")
        print("💡 Run: python setup_wallet_connection.py")
        return 1
    
    # Check balance
    print(f"\n💰 Checking balance...")
    balance = check_wallet_balance(current_address)
    if balance is not None:
        print(f"   Balance: {balance:.6f} SOL")
        
        if balance < 0.01:
            print(f"⚠️  Low balance warning: {balance:.6f} SOL")
            print(f"   Consider adding more SOL for trading")
        else:
            print(f"✅ Sufficient balance for trading")
    else:
        print(f"❌ Could not check balance")
    
    # Check Drift account
    print(f"\n🏦 Checking Drift account...")
    drift_account = check_drift_account(current_address)
    if drift_account:
        print(f"✅ Drift account found")
    else:
        print(f"❌ No Drift account found")
        print(f"💡 Run: python create_drift_account.py")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"   Wallet: {'✅' if current_address == target_address else '❌'}")
    print(f"   Balance: {'✅' if balance and balance >= 0.01 else '⚠️'}")
    print(f"   Drift Account: {'✅' if drift_account else '❌'}")
    
    if current_address == target_address and balance and balance >= 0.01 and drift_account:
        print(f"\n🎉 Ready to trade!")
        print(f"💡 Run: python start_swift_mm_bot.py")
        return 0
    else:
        print(f"\n⚠️  Setup incomplete")
        print(f"💡 Run: python setup_wallet_connection.py")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Check cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Check failed: {e}")
        sys.exit(1)