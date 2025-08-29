#!/usr/bin/env python3
"""
Check SOL balance for your wallet
"""

import asyncio
import json
import httpx
from typing import Dict, Any

class WalletBalanceChecker:
    """Check SOL balance using Helius RPC"""

    def __init__(self):
        self.rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        self.explorer_base = "https://explorer.solana.com"

    async def get_balance(self, public_key: str) -> Dict[str, Any]:
        """Get SOL balance for a wallet"""
        print(f"\n💰 Checking balance for: {public_key}")

        try:
            # Prepare RPC request
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [public_key]
            }

            headers = {
                "Content-Type": "application/json"
            }

            # Make RPC request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.rpc_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )

            if response.status_code == 200:
                result = response.json()
                
                if "result" in result and "value" in result["result"]:
                    balance_lamports = result["result"]["value"]
                    balance_sol = balance_lamports / 1_000_000_000
                    
                    print(f"✅ Balance: {balance_sol:.6f} SOL ({balance_lamports} lamports)")
                    
                    return {
                        'success': True,
                        'balance_sol': balance_sol,
                        'balance_lamports': balance_lamports,
                        'public_key': public_key
                    }
                elif "error" in result:
                    error_msg = f"RPC Error: {result['error']}"
                    print(f"❌ Failed: {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'public_key': public_key
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ Failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'public_key': public_key
                }

        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                'success': False,
                'error': str(e),
                'public_key': public_key
            }

async def main():
    """Main function"""
    print("💰 WALLET BALANCE CHECKER")
    print("=" * 50)

    checker = WalletBalanceChecker()

    # Your wallet public key
    wallet_public_key = "6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW"

    print(f"\n🎯 Checking wallet: {wallet_public_key}")

    # Check balance
    result = await checker.get_balance(wallet_public_key)

    if result['success']:
        balance_sol = result['balance_sol']
        
        print(f"\n📊 BALANCE SUMMARY")
        print("=" * 30)
        print(f"   • Public Key: {result['public_key']}")
        print(f"   • SOL Balance: {balance_sol:.6f} SOL")
        
        if balance_sol >= 0.1:
            print(f"\n✅ SUFFICIENT FUNDS!")
            print(f"   • You have {balance_sol:.6f} SOL for trading")
            print(f"   • Ready to start the JIT Market Maker Bot!")
        else:
            print(f"\n⚠️  INSUFFICIENT FUNDS")
            print(f"   • You need at least 0.1 SOL for trading")
            print(f"   • Current balance: {balance_sol:.6f} SOL")
            print(f"   • Try airdrop again later or use web faucet")
        
        print(f"\n🔗 Explorer: {checker.explorer_base}/address/{wallet_public_key}?cluster=devnet")
    else:
        print(f"\n❌ FAILED: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
