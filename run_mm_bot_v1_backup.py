#!/usr/bin/env python3
"""
🚀 MM Bot Runner - Market Maker Bot
Runs the JIT (Just-In-Time) bot for market making on Drift
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the libs directory to the path
sys.path.append(str(Path(__file__).parent / "libs"))

from libs.drift.client import build_client_from_config

async def run_mm_bot():
    """Run the MM (JIT) bot for market making"""
    print("🚀 Starting MM Bot - Market Maker")
    print("=" * 50)

    try:
        # Check if we're in mock mode
        use_mock = os.getenv('USE_MOCK', 'true').lower() == 'true'

        if not use_mock:
            # Only check wallet in live mode
            wallet_path = ".beta_dev_wallet.json"
            if not Path(wallet_path).exists():
                print("❌ Wallet file .beta_dev_wallet.json not found!")
                print("💡 Please create a wallet with: solana-keygen new --outfile .beta_dev_wallet.json")
                print("   Or run: python setup_beta_wallet.py")
                return
        else:
            print("🔧 Running in MOCK mode - no wallet required")

        # Set environment variables
        os.environ['DRIFT_RPC_URL'] = "https://api.devnet.solana.com"
        os.environ['DRIFT_WS_URL'] = "wss://api.devnet.solana.com"
        os.environ['DRIFT_CLUSTER'] = "devnet"

        # Set wallet path for real transactions
        os.environ['DRIFT_KEYPAIR_PATH'] = ".swift_test_wallet.json"

        print("🔗 Connecting to DEV blockchain...")
        print(f"   RPC: {os.environ['DRIFT_RPC_URL']}")
        print(f"   Wallet: {os.environ['DRIFT_KEYPAIR_PATH']}")

        # Build client from config
        client = await build_client_from_config("configs/core/drift_client.yaml")
        print("✅ Connected to DEV blockchain")

        # Initialize the drift client (subscribe to accounts)
        if hasattr(client, 'initialize'):
            print("🔧 Initializing drift client...")
            await client.initialize()
            print("✅ Drift client initialized")

        # Load JIT bot configuration
        import yaml
        try:
            with open("configs/jit/params.yaml", 'r') as f:
                jit_config = yaml.safe_load(f)
            spread_bps = float(jit_config["spread_bps"]["base"])
            print(f"📊 Loaded JIT config - spread: {spread_bps} bps")
        except Exception as e:
            print(f"⚠️  Could not load JIT config, using default spread: {e}")
            spread_bps = 2.5  # Default 2.5 bps spread

        # Initialize Prometheus metrics
        from prometheus_client import start_http_server, Gauge, Counter
        start_http_server(9109)
        spread_g = Gauge("jit_spread_bps", "Current spread bps")
        quotes_c = Counter("jit_quotes_total", "Total quotes placed")

        print("📊 Prometheus metrics server started on port 9109")
        print("⚡ MM Bot running in LIVE DEV mode")
        print("🎯 Market Making Strategy: JIT with dynamic spreads")

        iteration = 0
        while True:
            try:
                # Get current orderbook (SYNCHRONOUS)
                print("📊 Fetching orderbook...")
                ob = client.get_orderbook()

                # Check if we have valid orderbook data
                if not ob.bids or not ob.asks:
                    print("⏳ Waiting for orderbook data...")
                    await asyncio.sleep(1)
                    continue

                # Calculate mid price from top of book
                mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
                print(".4f")

                # Calculate bid/ask prices with dynamic spread
                bid = mid * (1 - spread_bps/2/10000)
                ask = mid * (1 + spread_bps/2/10000)

                # Create market making orders
                from libs.drift.client import Order, OrderSide

                bid_order = Order(
                    side=OrderSide.BUY,
                    price=round(bid, 4),
                    size_usd=150.0  # Minimum 10M base units for SOL-PERP
                )

                ask_order = Order(
                    side=OrderSide.SELL,
                    price=round(ask, 4),
                    size_usd=150.0  # Minimum 10M base units for SOL-PERP
                )

                # Place orders with async/sync detection
                print(f"📈 Placing orders - Bid: ${bid:.4f}, Ask: ${ask:.4f}")

                import asyncio
                try:
                    if asyncio.iscoroutinefunction(client.place_order):
                        # Real client - use await
                        print("🔄 Placing BUY order...")
                        bid_id = await client.place_order(bid_order)
                        print(f"✅ BUY order placed: {bid_id}")

                        print("🔄 Placing SELL order...")
                        ask_id = await client.place_order(ask_order)
                        print(f"✅ SELL order placed: {ask_id}")
                    else:
                        # Mock client - no await needed
                        print("🔄 Placing BUY order...")
                        bid_id = client.place_order(bid_order)
                        print(f"✅ BUY order placed: {bid_id}")

                        print("🔄 Placing SELL order...")
                        ask_id = client.place_order(ask_order)
                        print(f"✅ SELL order placed: {ask_id}")

                    print(f"🎯 Both orders completed - Bid: {bid_id}, Ask: {ask_id}")
                except Exception as e:
                    print(f"❌ Error placing orders: {e}")
                    import traceback
                    traceback.print_exc()

                # Update metrics
                quotes_c.inc(2)
                spread_g.set(spread_bps)

                iteration += 1
                if iteration % 5 == 0:
                    print(f"⚡ MM Bot: Completed {iteration} iterations, Spread: {spread_bps} bps")

                await asyncio.sleep(0.9)  # Fast execution for JIT

            except Exception as e:
                print(f"❌ MM Bot error: {e}")
                await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("\n⏹️  MM Bot stopped by user")
    except Exception as e:
        print(f"❌ MM Bot failed to start: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_mm_bot())
