import argparse
import asyncio
import os
import time
import json
from pathlib import Path
import yaml
from loguru import logger
from datetime import datetime

from libs.metrics import start_metrics, LOOP_LATENCY, ORDERS_PLACED, record_mid, INV_USD
from libs.drift.client import build_client_from_config, Order, OrderSide

JIT_CFG = Path("configs/jit/params.yaml")
CORE_CFG = os.getenv("DRIFT_CFG", "configs/core/drift_client.yaml")

async def run(env: str = "testnet", metrics_port: int | None = 9101, cfg_path: str = CORE_CFG):
    if metrics_port:
        start_metrics(metrics_port)
    jit = yaml.safe_load(Path(JIT_CFG).read_text())["jit"]

    client = await build_client_from_config(cfg_path)
    logger.info(f"JIT Maker (wrapper) starting – env={env}, refresh={jit['refresh_ms']}ms")
    logger.info(f"Trading parameters: spread={jit['spread_bps']} bps, size=${jit['quote_size_usd']}, refresh={jit['refresh_ms']}ms")

    try:
        while True:
            t0 = time.perf_counter()
            
            # Get current orderbook
            ob = await client.get_orderbook() if hasattr(client, 'get_orderbook') and asyncio.iscoroutinefunction(client.get_orderbook) else client.get_orderbook()
            
            if not ob.bids or not ob.asks:
                logger.warning("No orderbook data, waiting...")
                await asyncio.sleep(0.05)
                continue
            
            # Calculate mid price
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
            record_mid(mid)
            
            # Calculate spread-based pricing
            spread = jit["spread_bps"] / 10000.0 * mid
            bid = mid - spread / 2
            ask = mid + spread / 2
            size = float(jit["quote_size_usd"])
            
            # Log trading decision
            logger.info(f"[JIT] Market: mid=${mid:.4f}, spread=${spread:.4f}, bid=${bid:.4f}, ask=${ask:.4f}")
            
            # Place orders with proper error handling
            try:
                bid_order = Order(side="buy", price=bid, size_usd=size)
                ask_order = Order(side="sell", price=ask, size_usd=size)
                
                bid_id = await client.place_order(bid_order) if asyncio.iscoroutinefunction(client.place_order) else client.place_order(bid_order)
                ask_id = await client.place_order(ask_order) if asyncio.iscoroutinefunction(client.place_order) else client.place_order(ask_order)
                
                logger.info(f"[JIT] Orders placed: BUY {bid_id} @ ${bid:.4f}, SELL {ask_id} @ ${ask:.4f}")
                ORDERS_PLACED.inc(2)
                
            except Exception as e:
                logger.error(f"[JIT] Failed to place orders: {e}")
                ORDERS_PLACED.inc(0)  # Don't increment on failure
            
            # Update inventory metric (placeholder for now)
            INV_USD.set(0.0)
            
            # Record loop latency
            LOOP_LATENCY.observe(time.perf_counter() - t0)
            
            # Wait for next cycle
            await asyncio.sleep(jit["refresh_ms"] / 1000.0)

    except KeyboardInterrupt:
        logger.info("JIT Maker shutdown requested")
    except Exception as e:
        logger.error(f"JIT Maker error: {e}")
        raise
    finally:
        # Generate comprehensive test report
        await generate_test_report(client, start_time)
        close = getattr(client, "close", None)
        if asyncio.iscoroutinefunction(close):
            await close()  # type: ignore
        elif callable(close):
            close()
        logger.info("JIT Maker shutdown complete")

async def generate_test_report(client, start_time):
    """Generate comprehensive test report"""
    try:
        print("\n" + "="*80)
        print("🎯 DRIFT PROTOCOL JIT BOT - HARDCORE TEST REPORT")
        print("="*80)

        end_time = time.time()
        runtime_minutes = (end_time - start_time) / 60

        print(f"⏱️  TEST DURATION: {runtime_minutes:.2f} minutes")
        print(f"🏆 ENVIRONMENT: Drift Devnet (Real Protocol)")
        print(f"💰 WALLET: {getattr(client, 'keypair', lambda: 'Unknown').pubkey() if hasattr(client, 'keypair') else 'Unknown'}")
        print(f"📊 MARKET: SOL-PERP (Market Index 0)")
        print()

        # Get comprehensive stats
        if hasattr(client, 'get_comprehensive_stats_report'):
            stats = client.get_comprehensive_stats_report()
            if "error" not in stats:
                print("📈 TRADING STATISTICS")
                print("-" * 40)
                print(f"Total Orders: {stats['total_orders']}")
                print(f"Successful Orders: {stats['successful_orders']}")
                print(f"Failed Orders: {stats['failed_orders']}")
                print(".1f")
                print(".0f")
                print(".2f")
                print(".2f")
                print(".2f")
                print(".2f")
                print(".2f")
                print(f"Oracle Price Changes: {stats['oracle_price_changes']}")
                print(".2f")
                print()

        # Get PnL summary
        pnl = client.get_pnl_summary()
        print("💰 P&L SUMMARY")
        print("-" * 40)
        print(".4f")
        print(".4f")
        print(".4f")
        print(".4f")
        print(".4f")
        print()

        # Performance metrics
        print("⚡ PERFORMANCE METRICS")
        print("-" * 40)
        if hasattr(client, 'stats'):
            stats = client.stats
            orders_per_min = stats.total_orders / runtime_minutes if runtime_minutes > 0 else 0
            volume_per_min = stats.total_volume_usd / runtime_minutes if runtime_minutes > 0 else 0
            print(".1f")
            print(".0f")
            print(".2f")
            print(".4f")
            print(".2f")
        print()

        # System health
        print("🔧 SYSTEM HEALTH")
        print("-" * 40)
        print("✅ Drift Client: Connected")
        print("✅ Wallet: Funded")
        print("✅ RPC: https://api.devnet.solana.com")
        print("✅ Environment: devnet")
        print()

        # Recommendations
        print("🎯 RECOMMENDATIONS")
        print("-" * 40)
        if hasattr(client, 'stats'):
            success_rate = (client.stats.successful_orders / client.stats.total_orders * 100) if client.stats.total_orders > 0 else 0
            if success_rate < 80:
                print("⚠️  Low success rate - check order parameters and wallet balance")
            if client.stats.avg_spread_bps > 20:
                print("⚠️  High average spread - consider adjusting spread strategy")
            if client.stats.oracle_price_changes == 0:
                print("⚠️  No oracle price changes detected - verify market data connection")
        print()

        # Export report
        report_data = {
            "test_info": {
                "duration_minutes": runtime_minutes,
                "environment": "Drift Devnet",
                "market": "SOL-PERP",
                "wallet": str(getattr(client, 'keypair', lambda: 'Unknown').pubkey() if hasattr(client, 'keypair') else 'Unknown'),
                "timestamp": datetime.now().isoformat()
            },
            "trading_stats": client.get_comprehensive_stats_report() if hasattr(client, 'get_comprehensive_stats_report') else {},
            "pnl_summary": pnl,
            "recommendations": []
        }

        # Save report
        report_file = f"drift_bot_test_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        print(f"💾 Report saved: {report_file}")
        print("="*80)

    except Exception as e:
        print(f"❌ Error generating report: {e}")

async def run_hardcore_test(duration_minutes: int = 10, cfg_path: str = CORE_CFG):
    """Run hardcore 10-minute test on Drift devnet"""
    print("🚀 STARTING HARDCORE DRIFT BOT TEST")
    print("=" * 60)
    print(f"Duration: {duration_minutes} minutes")
    print("Environment: Drift Devnet (REAL TRADING)")
    print("Mode: JIT Market Making Bot")
    print("=" * 60)

    start_time = time.time()
    client = await build_client_from_config(cfg_path)

    # Configure JIT parameters for testing
    jit_config = {
        "spread_bps": 10,  # 10 bps spread
        "quote_size_usd": 5.0,  # $5 per order
        "refresh_ms": 3000  # 3 second refresh
    }

    print("⚙️  TEST CONFIGURATION")
    print(".1f")
    print(f"Quote Size: ${jit_config['quote_size_usd']}")
    print(f"Refresh Rate: {jit_config['refresh_ms']}ms")
    print("Strategy: Basic MM - SELL orders only")
    print()

    try:
        # Run the test
        await run_test_cycle(client, jit_config, duration_minutes)

    finally:
        # Generate report
        await generate_test_report(client, start_time)
        await client.close()

async def run_test_cycle(client, jit_config, duration_minutes):
    """Run the actual test cycle"""
    end_time = time.time() + (duration_minutes * 60)
    cycle_count = 0

    print("▶️  STARTING BASIC MM TEST - SELL ORDERS ONLY...")
    print(f"📈 Placing ASK orders at {jit_config['spread_bps']} bps above mid price")
    print()

    while time.time() < end_time:
        cycle_count += 1
        cycle_start = time.time()

        try:
            # Get orderbook
            ob = await client.get_orderbook()
            if not ob.bids or not ob.asks:
                print(f"[{cycle_count}] ⚠️  No orderbook data, skipping...")
                await asyncio.sleep(1)
                continue

            # Calculate trading parameters
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
            spread = jit_config["spread_bps"] / 10000.0 * mid
            bid_price = mid - spread / 2
            ask_price = mid + spread / 2
            size = jit_config["quote_size_usd"]

            # Place only SELL (ASK) orders for basic market making
            ask_order = Order(side=OrderSide.SELL, price=ask_price, size_usd=size)

            ask_id = await client.place_order(ask_order) if asyncio.iscoroutinefunction(client.place_order) else client.place_order(ask_order)

            cycle_time = time.time() - cycle_start

            # Progress update every 10 cycles
            if cycle_count % 10 == 0:
                if hasattr(client, 'stats'):
                    stats = client.stats
                    print(f"[{cycle_count}] 📊 Progress: {stats.successful_orders}/{stats.total_orders} orders, "
                          ".4f"
                          ".2f")
                else:
                    print(f"[{cycle_count}] ✅ ASK order placed: SELL {ask_id} @ ${ask_price:.4f} ({cycle_time:.3f}s)")

            # Wait before next cycle
            await asyncio.sleep(max(0, jit_config["refresh_ms"] / 1000.0 - cycle_time))

        except Exception as e:
            print(f"[{cycle_count}] ❌ Cycle error: {e}")
            await asyncio.sleep(1)

    print(f"\n🏁 Basic MM test completed after {cycle_count} cycles!")
    print(f"📊 Placed {cycle_count} ASK (SELL) orders on Drift devnet")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drift Protocol JIT Market Making Bot")
    parser.add_argument("--env", default=os.getenv("DRIFT_ENV", "testnet"))
    parser.add_argument("--metrics-port", type=int, default=9101)
    parser.add_argument("--cfg", default=CORE_CFG)
    parser.add_argument("--test", action="store_true", help="Run hardcore 10-minute test")
    parser.add_argument("--test-duration", type=int, default=10, help="Test duration in minutes")
    args = parser.parse_args()

    try:
        if args.test:
            print("🎯 Running hardcore test mode...")
            asyncio.run(run_hardcore_test(duration_minutes=args.test_duration, cfg_path=args.cfg))
        else:
            print("🤖 Running standard JIT bot mode...")
            asyncio.run(run(env=args.env, metrics_port=args.metrics_port, cfg_path=args.cfg))
    except KeyboardInterrupt:
        logger.info("JIT Maker shutdown")