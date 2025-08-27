#!/usr/bin/env python3
"""
🚀 SINGLE MM BOT RUNNER - DEV Environment
Runs only the JIT (Market Maker) bot in live DEV mode
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the libs directory to the path
sys.path.append(str(Path(__file__).parent / "libs"))

from libs.drift.client import build_client_from_config

async def run_mm_bot_only():
    """Run only the MM (JIT) bot in DEV environment"""
    print("🚀 Starting MM Bot in DEV Environment")
    print("=" * 50)

    try:
        # Check if wallet exists
        if not Path(".beta_dev_wallet.json").exists():
            print("❌ Wallet file .beta_dev_wallet.json not found!")
            print("💡 Please create a wallet with: solana-keygen new --outfile .beta_dev_wallet.json")
            return

        # Set environment variables for real client
        os.environ['DRIFT_RPC_URL'] = "https://api.devnet.solana.com"
        os.environ['DRIFT_WS_URL'] = "wss://api.devnet.solana.com"
        os.environ['DRIFT_KEYPAIR_PATH'] = ".beta_dev_wallet.json"
        os.environ['DRIFT_CLUSTER'] = "devnet"

        print("🔗 Connecting to DEV blockchain...")
        print(f"   RPC: {os.environ['DRIFT_RPC_URL']}")
        print(f"   Wallet: {os.environ['DRIFT_KEYPAIR_PATH']}")

        # Build client from config
        client = await build_client_from_config("configs/core/drift_client.yaml")
        print("✅ Connected to DEV blockchain")
        
        # Check what type of client we got
        print(f"🔍 Client type: {type(client).__name__}")
        print(f"🔍 Client attributes: {[attr for attr in dir(client) if not attr.startswith('_')]}")
        
        # Initialize the real Drift client
        if hasattr(client, 'initialize'):
            print("🔧 Initializing Drift client...")
            try:
                await client.initialize()
                print("✅ Drift client initialized successfully")
            except Exception as init_error:
                print(f"⚠️  Client initialization failed: {init_error}")
                print("🔄 Continuing with available functionality...")
        else:
            print("ℹ️  Client does not have initialize method")

        # Load JIT bot configuration
        import yaml
        try:
            with open("configs/jit/params.yaml", 'r') as f:
                jit_config = yaml.safe_load(f)
            spread_bps = float(jit_config["spread_bps"]["base"])
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
        print(f"📊 Using spread: {spread_bps} bps")

        iteration = 0
        while True:
            try:
                # Get current orderbook (SYNCHRONOUS - no await needed!)
                print("📊 Fetching orderbook...")
                try:
                    ob = client.get_orderbook()  # ✅ NO AWAIT - it returns the orderbook directly
                    print(f"✅ Orderbook fetched: {len(ob.bids)} bids, {len(ob.asks)} asks")
                except Exception as ob_error:
                    print(f"❌ Orderbook fetch failed: {ob_error}")
                    print("⏳ Waiting before retry...")
                    await asyncio.sleep(5)
                    continue
                
                # Check if we have valid orderbook data
                if not ob.bids or not ob.asks:
                    print("⏳ Waiting for orderbook data...")
                    await asyncio.sleep(1)
                    continue

                # Create safe snapshot (prevents await misuse)
                from libs.market import snapshot_from_driver_ob, SafeAwaitError

                try:
                    snapshot = snapshot_from_driver_ob(ob)
                    if not snapshot.is_valid():
                        print("⏳ Waiting for valid orderbook data...")
                        await asyncio.sleep(1)
                        continue

                    # Use snapshot methods safely (no await needed)
                    mid = snapshot.mid_price()
                    current_spread = snapshot.spread_bps()

                    if mid <= 0:
                        print("⏳ Waiting for valid mid price...")
                        await asyncio.sleep(1)
                        continue

                    # Calculate bid/ask prices with dynamic spread
                    bid = mid * (1 - spread_bps/2/10000)
                    ask = mid * (1 + spread_bps/2/10000)

                    print(f"📊 Current spread: {current_spread:.2f} bps")

                except SafeAwaitError as e:
                    print(f"❌ Guarded misuse prevented: {e}")
                    await asyncio.sleep(5)
                    continue
                except Exception as snapshot_error:
                    print(f"⚠️  Snapshot creation failed, falling back to direct access: {snapshot_error}")
                    # Fallback to direct access if snapshot fails
                    mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
                    bid = mid * (1 - spread_bps/2/10000)
                    ask = mid * (1 + spread_bps/2/10000)

                # Create market making orders
                from libs.drift.client import Order, OrderSide

                bid_order = Order(
                    side=OrderSide.BUY,
                    price=round(bid, 4),
                    size_usd=25.0  # Conservative size for DEV
                )

                ask_order = Order(
                    side=OrderSide.SELL,
                    price=round(ask, 4),
                    size_usd=25.0  # Conservative size for DEV
                )

                # Place orders (handle both sync and async clients)
                print(f"📈 Placing orders - Mid: ${mid:.4f}, Bid: ${bid:.4f}, Ask: ${ask:.4f}")
                
                # Check if place_order is async or sync
                import asyncio
                try:
                    if asyncio.iscoroutinefunction(client.place_order):
                        # Real client - use await
                        bid_id = await client.place_order(bid_order)
                        ask_id = await client.place_order(ask_order)
                    else:
                        # Mock client - no await needed
                        bid_id = client.place_order(bid_order)
                        ask_id = client.place_order(ask_order)
                    
                    print(f"✅ Orders placed: Bid={bid_id}, Ask={ask_id}")
                    
                except Exception as order_error:
                    print(f"❌ Order placement failed: {order_error}")
                    bid_id = ask_id = "failed"

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

    except Exception as e:
        print(f"❌ MM Bot failed to start: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_mm_bot_only())
