#!/usr/bin/env python3
"""
Cancel all existing orders on Drift wallet
"""

import asyncio
import base58
from typing import Optional
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from anchorpy import Wallet

# DriftPy imports
try:
    from driftpy.drift_client import DriftClient
    from driftpy.types import OrderParams, OrderType, PositionDirection, MarketType
    from driftpy.accounts import get_perp_market_account
    DRIFTPY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  DriftPy import error: {e}")
    DRIFTPY_AVAILABLE = False

class OrderCanceler:
    """Cancel all orders on Drift wallet"""

    def __init__(self, private_key_b58: str):
        self.private_key_b58 = private_key_b58
        self.connection = None
        self.drift_client = None
        self.wallet = None
        self.rpc_url = "https://api.devnet.solana.com"
        self.drift_program_id = "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"

    async def initialize(self):
        """Initialize Drift client with wallet"""
        print("🔧 Initializing Drift client...")

        if not DRIFTPY_AVAILABLE:
            raise RuntimeError("DriftPy not available - run: pip install driftpy")

        try:
            # Decode private key
            private_key_bytes = base58.b58decode(self.private_key_b58)

            # Create keypair
            if len(private_key_bytes) == 32:
                keypair = Keypair.from_seed(private_key_bytes)
            elif len(private_key_bytes) == 64:
                keypair = Keypair.from_bytes(private_key_bytes)
            else:
                raise ValueError(f"Invalid key length: {len(private_key_bytes)}")

            self.wallet = Wallet(keypair)
            print(f"✅ Loaded wallet: {self.wallet.public_key}")

            # Create connection
            from solana.rpc.async_api import AsyncClient
            self.connection = AsyncClient(self.rpc_url)

            # Create Drift client
            self.drift_client = DriftClient(
                connection=self.connection,
                wallet=self.wallet,
                env="devnet"
            )

            # Initialize user account
            await self.drift_client.add_user(0)
            await self.drift_client.subscribe()

            print("✅ Drift client initialized")

        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            raise

    async def get_open_orders(self) -> list:
        """Get all open orders"""
        try:
            user = self.drift_client.get_user()
            if not user:
                return []

            orders = []
            for i in range(32):  # Check all order slots
                order = user.get_order(i)
                if order and order.status == 0:  # Active order
                    orders.append({
                        'slot': i,
                        'market_index': order.market_index,
                        'direction': 'LONG' if order.direction == 0 else 'SHORT',
                        'base_asset_amount': order.base_asset_amount,
                        'price': order.price,
                        'order_type': order.order_type
                    })

            return orders

        except Exception as e:
            print(f"❌ Failed to get open orders: {e}")
            return []

    async def cancel_all_orders(self) -> dict:
        """Cancel all open orders"""
        print("🔄 Getting open orders...")

        open_orders = await self.get_open_orders()

        if not open_orders:
            print("✅ No open orders found")
            return {'success': True, 'cancelled': 0, 'orders': []}

        print(f"📋 Found {len(open_orders)} open orders:")
        for order in open_orders:
            print(f"  - Slot {order['slot']}: {order['direction']} {order['base_asset_amount']} @ {order['price']}")

        cancelled = 0
        failed = 0

        for order in open_orders:
            try:
                print(f"🗑️  Cancelling order in slot {order['slot']}...")

                # Cancel order by market index and order ID
                signature = await self.drift_client.cancel_order(
                    order_id=order['slot'],
                    market_index=order['market_index']
                )

                print(f"✅ Cancelled order {order['slot']}: {signature}")
                cancelled += 1

                # Small delay between cancellations
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"❌ Failed to cancel order {order['slot']}: {e}")
                failed += 1

        return {
            'success': failed == 0,
            'cancelled': cancelled,
            'failed': failed,
            'orders': open_orders
        }

    async def close(self):
        """Cleanup connections"""
        if self.drift_client:
            try:
                await self.drift_client.unsubscribe()
            except:
                pass

        if self.connection:
            await self.connection.close()

async def cancel_orders_for_wallet(private_key_b58: str, wallet_name: str):
    """Cancel all orders for a specific wallet"""
    print(f"\n🔑 Processing wallet: {wallet_name}")
    print("=" * 50)

    canceler = OrderCanceler(private_key_b58)

    try:
        await canceler.initialize()

        # Show wallet balance first
        balance_response = await canceler.connection.get_balance(canceler.wallet.public_key)
        balance_sol = balance_response.value / 1e9
        print(".4f")

        # Cancel all orders
        result = await canceler.cancel_all_orders()

        # Show results
        if result['success']:
            print("🎉 SUCCESS!")
            print(f"   ✅ Cancelled: {result['cancelled']} orders")
            if result['failed'] > 0:
                print(f"   ⚠️  Failed: {result['failed']} orders")
        else:
            print("⚠️  PARTIAL SUCCESS")
            print(f"   ✅ Cancelled: {result['cancelled']} orders")
            print(f"   ❌ Failed: {result['failed']} orders")

        return result

    except Exception as e:
        print(f"❌ Error processing wallet: {e}")
        return {'success': False, 'error': str(e)}

    finally:
        await canceler.close()

async def main():
    """Main function to cancel orders for all wallets"""
    print("🗑️  CANCEL ALL ORDERS ON DRIFT")
    print("=" * 50)

    # Your wallet private keys
    wallets = [
        {
            'name': 'Wallet 1 (32-byte)',
            'private_key': '6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW',
            'public_key': 'G4aTeEx1pVMXcMKDjnnEyucqxmi3StxcAsLE9CcQZGzD'
        },
        {
            'name': 'Wallet 2 (64-byte)',
            'private_key': '4M7ojLUx4eRC8GtDq4rw8h77FPqXsuYQXTKhKNSKEpmD7TbZPZd9K5wK9HGcidFvGxSVryRCz38un4sgHtYn8Tzi',
            'public_key': '6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW'
        }
    ]

    total_cancelled = 0
    total_failed = 0

    for wallet in wallets:
        result = await cancel_orders_for_wallet(wallet['private_key'], wallet['name'])

        if 'cancelled' in result:
            total_cancelled += result['cancelled']
        if 'failed' in result:
            total_failed += result['failed']

    # Summary
    print("\n📊 FINAL SUMMARY")
    print("=" * 50)
    print(f"✅ Total orders cancelled: {total_cancelled}")
    if total_failed > 0:
        print(f"❌ Total orders failed: {total_failed}")

    if total_cancelled > 0:
        print("🎉 Order cancellation complete!")
        print("💡 Your order slots are now cleared and ready for new orders")
    else:
        print("ℹ️  No orders were found to cancel")

if __name__ == "__main__":
    asyncio.run(main())
