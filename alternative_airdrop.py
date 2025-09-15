#!/usr/bin/env python3
"""
Try alternative RPC endpoints for SOL airdrops
"""

import asyncio
import json
import httpx
from typing import Dict, Any

class AlternativeAirdrop:
    """Try multiple RPC endpoints for SOL airdrops"""

    def __init__(self):
        self.endpoints = [
            {
                'name': 'QuickNode Devnet',
                'url': 'https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494'
            },
            {
                'name': 'GenesysGo Devnet',
                'url': 'https://ssc-dao.genesysgo.net'
            },
            {
                'name': 'Serum Devnet',
                'url': 'https://solana-api.projectserum.com'
            }
        ]
        self.explorer_base = "https://explorer.solana.com"

    async def try_airdrop(self, endpoint: Dict, public_key: str, amount_sol: float = 1.0) -> Dict[str, Any]:
        """Try airdrop on a specific endpoint"""
        print(f"\n🪂 Trying {endpoint['name']}: {endpoint['url']}")
        print(f"   Requesting {amount_sol} SOL for: {public_key}")

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
                    endpoint['url'],
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )

            if response.status_code == 200:
                result = response.json()
                
                if "result" in result:
                    signature = result["result"]
                    print(f"✅ SUCCESS on {endpoint['name']}!")
                    print(f"   📋 Transaction Signature: {signature}")
                    print(f"   🔗 View on Explorer: {self.explorer_base}/tx/{signature}?cluster=devnet")

                    return {
                        'success': True,
                        'endpoint': endpoint['name'],
                        'signature': signature,
                        'amount': amount_sol,
                        'public_key': public_key
                    }
                elif "error" in result:
                    error_msg = f"RPC Error: {result['error']}"
                    print(f"   ❌ Failed: {error_msg}")
                    return {
                        'success': False,
                        'endpoint': endpoint['name'],
                        'error': error_msg,
                        'public_key': public_key
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:100]}..."
                print(f"   ❌ Failed: {error_msg}")
                return {
                    'success': False,
                    'endpoint': endpoint['name'],
                    'error': error_msg,
                    'public_key': public_key
                }

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return {
                'success': False,
                'endpoint': endpoint['name'],
                'error': str(e),
                'public_key': public_key
            }

    async def try_all_endpoints(self, public_key: str, amount_sol: float = 1.0):
        """Try airdrop on all available endpoints"""
        print("🪂 ALTERNATIVE AIRDROP ENDPOINTS")
        print("=" * 60)
        print("💰 Trying multiple RPC endpoints for SOL airdrop")

        successful_airdrops = []
        failed_airdrops = []

        for endpoint in self.endpoints:
            result = await self.try_airdrop(endpoint, public_key, amount_sol)
            
            if result['success']:
                successful_airdrops.append(result)
                # If we succeed on one endpoint, we can stop
                break
            else:
                failed_airdrops.append(result)
            
            # Wait a bit between attempts
            if endpoint != self.endpoints[-1]:
                print("   ⏰ Waiting 2 seconds before next attempt...")
                await asyncio.sleep(2)

        # Summary
        print("\n📊 AIRDROP SUMMARY")
        print("=" * 60)

        if successful_airdrops:
            print("✅ SUCCESSFUL AIRDROPS:")
            for drop in successful_airdrops:
                print(f"   • {drop['endpoint']}: {drop['amount']} SOL")
                print(f"     Signature: {drop['signature']}")
                print(f"     Explorer: {self.explorer_base}/tx/{drop['signature']}?cluster=devnet")
        else:
            print("❌ NO SUCCESSFUL AIRDROPS")

        if failed_airdrops:
            print("\n❌ FAILED ATTEMPTS:")
            for drop in failed_airdrops:
                print(f"   • {drop['endpoint']}: {drop['error']}")

        return successful_airdrops, failed_airdrops

async def main():
    """Main function"""
    print("🪂 ALTERNATIVE SOLANA AIRDROP")
    print("=" * 60)
    print("💰 Trying multiple RPC endpoints to get SOL")

    airdropper = AlternativeAirdrop()

    # Your wallet public key
    wallet_public_key = "G4aTeEx1pVMXcMKDjnnEyucqxmi3StxcAsLE9CcQZGzD"

    print(f"\n🎯 Target wallet: {wallet_public_key}")

    # Try all endpoints
    successful, failed = await airdropper.try_all_endpoints(wallet_public_key, amount_sol=1.0)

    if successful:
        print("\n🎉 SUCCESS! You now have SOL for trading!")
        print("\n💡 NEXT STEPS:")
        print("   1. Wait 30-60 seconds for transaction to confirm")
        print("   2. Check your balance: python check_wallet_funds.py")
        print("   3. Start your JIT Market Maker Bot!")
    else:
        print("\n😔 All airdrop attempts failed")
        print("\n💡 ALTERNATIVES:")
        print("   1. Wait 24 hours and try again (rate limits)")
        print("   2. Use the web faucet: https://faucet.solana.com/")
        print("   3. Ask someone with SOL to send you some")
        print("   4. Use a different wallet/account")

if __name__ == "__main__":
    asyncio.run(main())
