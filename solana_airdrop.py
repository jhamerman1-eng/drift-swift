#!/usr/bin/env python3
"""
Request SOL airdrops for your wallets on Solana devnet
"""

import asyncio
import time
import requests
from typing import Dict, Any

class SolanaAirdrop:
    """Request SOL from Solana devnet faucet"""

    def __init__(self):
        self.faucet_url = "https://faucet.solana.com/request"
        self.explorer_base = "https://explorer.solana.com"
        self.amount_lamports = 1_000_000_000  # 1 SOL = 1e9 lamports

    async def request_airdrop(self, public_key: str, amount_sol: float = 1.0) -> Dict[str, Any]:
        """Request SOL airdrop for a wallet"""
        print(f"\n🪂 Requesting {amount_sol} SOL airdrop for: {public_key}")

        try:
            # Convert SOL to lamports
            amount_lamports = int(amount_sol * 1_000_000_000)

            # Prepare request data
            data = {
                "recipient": public_key,
                "amount": amount_lamports
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            # Make request to faucet
            response = requests.post(self.faucet_url, json=data, headers=headers)

            if response.status_code == 200:
                result = response.json()
                print("✅ Airdrop request successful!")
                print(f"   📋 Transaction Signature: {result.get('signature', 'N/A')}")
                print(f"   🔗 View on Explorer: {self.explorer_base}/tx/{result.get('signature', '')}?cluster=devnet")

                return {
                    'success': True,
                    'signature': result.get('signature'),
                    'amount': amount_sol,
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

    async def wait_for_confirmation(self, signature: str, public_key: str):
        """Wait for transaction confirmation"""
        print("⏳ Waiting for transaction confirmation...")

        # Wait a bit for the transaction to be processed
        await asyncio.sleep(5)

        # Check transaction status
        explorer_url = f"{self.explorer_base}/tx/{signature}?cluster=devnet"
        print(f"🔍 Check status: {explorer_url}")

        return explorer_url

async def airdrop_to_wallets():
    """Request airdrops for all wallets"""
    print("🪂 SOLANA DEVNET AIRDROP REQUESTER")
    print("=" * 50)
    print("💰 Requesting SOL for trading fees and margin")

    airdropper = SolanaAirdrop()

    # Your wallet public keys
    wallets = [
        {
            'name': 'Wallet 1 (32-byte seed)',
            'public_key': 'G4aTeEx1pVMXcMKDjnnEyucqxmi3StxcAsLE9CcQZGzD'
        },
        {
            'name': 'Wallet 2 (64-byte secret)',
            'public_key': '6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW'
        }
    ]

    successful_airdrops = []
    failed_airdrops = []

    for wallet in wallets:
        print(f"\n🎯 Processing {wallet['name']}")

        # Request airdrop
        result = await airdropper.request_airdrop(wallet['public_key'], amount_sol=1.0)

        if result['success']:
            successful_airdrops.append(result)

            # Wait for confirmation
            if result.get('signature'):
                await airdropper.wait_for_confirmation(result['signature'], wallet['public_key'])
        else:
            failed_airdrops.append(result)

        # Rate limiting - wait between requests
        if wallet != wallets[-1]:  # Don't wait after the last wallet
            print("⏰ Waiting 3 seconds before next request...")
            await asyncio.sleep(3)

    # Summary
    print("\n📊 AIRDROP SUMMARY")
    print("=" * 50)

    if successful_airdrops:
        print("✅ SUCCESSFUL AIRDROPS:")
        total_sol = 0
        for drop in successful_airdrops:
            print(f"   • {drop['public_key'][:8]}...: {drop['amount']} SOL")
            total_sol += drop['amount']
        print(".1f")

    if failed_airdrops:
        print("❌ FAILED AIRDROPS:")
        for drop in failed_airdrops:
            print(f"   • {drop['public_key'][:8]}...: {drop['error']}")

    print("\n💡 NEXT STEPS:")
    print("   1. Wait 30-60 seconds for transactions to confirm")
    print("   2. Check your balances with: python check_wallet_funds.py")
    print("   3. Start trading with your bots!")

    print("\n🔗 Useful Links:")
    print("   • Solana Devnet Faucet: https://faucet.solana.com/")
    print("   • Drift Devnet UI: https://beta.drift.trade/")
    print("   • Wallet 4 Explorer: https://explorer.solana.com/address/G4aTeEx1pVMXcMKDjnnEyucqxmi3StxcAsLE9CcQZGzD?cluster=devnet")
    print("   • Wallet 3 Explorer: https://explorer.solana.com/address/MBVHQtmMxT9YRFrcdALYpQnsA6vtzBpZASm5LBXJ3VV?cluster=devnet")

    return len(successful_airdrops), len(failed_airdrops)

async def check_rate_limits():
    """Check faucet rate limits and recommendations"""
    print("ℹ️  FAUCET INFORMATION")
    print("=" * 50)
    print("📋 Solana Devnet Faucet Limits:")
    print("   • Maximum 2 SOL per request")
    print("   • Rate limited (typically 1 request per minute per IP)")
    print("   • May have daily limits")
    print("   • Sometimes requires captcha verification")
    print()
    print("💡 If airdrop fails:")
    print("   1. Wait a few minutes and try again")
    print("   2. Try the web interface: https://faucet.solana.com/")
    print("   3. Use a different IP if rate limited")
    print("   4. Check if faucet is temporarily down")

async def main():
    """Main function"""
    await check_rate_limits()
    print()

    success_count, fail_count = await airdrop_to_wallets()

    if success_count == 0:
        print("\n❌ No airdrops succeeded")
        print("💡 Try the web faucet or wait before retrying")
    elif fail_count > 0:
        print(f"\n⚠️  {fail_count} airdrop(s) failed - check errors above")

if __name__ == "__main__":
    asyncio.run(main())

