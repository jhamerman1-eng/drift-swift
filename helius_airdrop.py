#!/usr/bin/env python3
"""
Request SOL airdrops using Helius RPC endpoint
"""

import asyncio
import json
import yaml
import httpx
from typing import Dict, Any

class HeliusAirdrop:
    """Request SOL from Solana devnet using Helius RPC"""

    def __init__(self):
        self.rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        self.explorer_base = "https://explorer.solana.com"

    async def request_airdrop(self, public_key: str, amount_sol: float = 1.0) -> Dict[str, Any]:
        """Request SOL airdrop for a wallet using RPC"""
        print(f"\n🪂 Requesting {amount_sol} SOL airdrop for: {public_key}")

        try:
            # Convert SOL to lamports
            amount_lamports = int(amount_sol * 1_000_000_000)

            # Prepare RPC request
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "requestAirdrop",
                "params": [
                    public_key,
                    amount_lamports
                ]
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
                
                if "result" in result:
                    signature = result["result"]
                    print("✅ Airdrop request successful!")
                    print(f"   📋 Transaction Signature: {signature}")
                    print(f"   🔗 View on Explorer: {self.explorer_base}/tx/{signature}?cluster=devnet")

                    return {
                        'success': True,
                        'signature': signature,
                        'amount': amount_sol,
                        'public_key': public_key
                    }
                elif "error" in result:
                    error_msg = f"RPC Error: {result['error']}"
                    print(f"❌ Airdrop failed: {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'public_key': public_key
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ Airdrop failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'public_key': public_key
                }

        except Exception as e:
            print(f"❌ Airdrop error: {e}")
            return {
                'success': False,
                'error': str(e),
                'public_key': public_key
            }

async def main():
    """Main function"""
    print("🪂 HELIUS RPC AIRDROP REQUESTER")
    print("=" * 50)
    print("💰 Requesting SOL for trading fees and margin")

    airdropper = HeliusAirdrop()

    # Load wallet from config
    cfg = yaml.safe_load(open("configs/core/drift_client.yaml", "r", encoding="utf-8"))
    secret = json.load(open(cfg["wallets"]["maker_keypair_path"], "r", encoding="utf-8"))
    from solders.keypair import Keypair
    kp = Keypair.from_bytes(bytes(secret))
    wallet_public_key = str(kp.pubkey())

    print(f"\n🎯 Processing wallet: {wallet_public_key}")

    # Request airdrop
    result = await airdropper.request_airdrop(wallet_public_key, amount_sol=1.0)

    if result['success']:
        print("\n✅ SUCCESS!")
        print(f"   • Public Key: {result['public_key']}")
        print(f"   • Amount: {result['amount']} SOL")
        print(f"   • Signature: {result['signature']}")
        
        print("\n💡 NEXT STEPS:")
        print("   1. Wait 30-60 seconds for transaction to confirm")
        print("   2. Check your balance with: python check_wallet_funds.py")
        print("   3. Start trading with your bot!")
        
        print(f"\n🔗 Explorer: {airdropper.explorer_base}/tx/{result['signature']}?cluster=devnet")
    else:
        print(f"\n❌ FAILED: {result['error']}")
        print("\n💡 Try again in a few minutes or use the web faucet")

if __name__ == "__main__":
    asyncio.run(main())
