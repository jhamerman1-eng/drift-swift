from __future__ import annotations
import argparse
import os
import signal
import sys
import time
import yaml
import asyncio
from pathlib import Path
from prometheus_client import start_http_server, Gauge, Counter

# Local import
from libs.drift.client import build_client_from_config, Order, OrderSide

RUNNING = True

def _sigterm(_signo, _frame):
    global RUNNING
    RUNNING = False

def load_yaml(path: Path) -> dict:
    with path.open("r") as f:
        return yaml.safe_load(f)

async def main():
    parser = argparse.ArgumentParser(description="JIT Maker Bot (Enhanced Mock)")
    parser.add_argument("--env", default=os.getenv("ENV", "testnet"))
    args = parser.parse_args()

    # Load configs
    core = load_yaml(Path("configs/core/drift_client.yaml"))
    jit = load_yaml(Path("configs/jit/params.yaml"))
    metrics_port = int(os.getenv("METRICS_PORT", "9300"))

    # Metrics
    start_http_server(metrics_port)
    spread_g = Gauge("jit_spread_bps", "Current spread bps")
    quotes_c = Counter("jit_quotes_total", "Total quotes placed")
    prints_c = Counter("jit_prints_total", "Total fills (stub)")

    # Initialize enhanced mock client
    client = await build_client_from_config("configs/core/drift_client.yaml")
    
    print(f"[JIT] env={args.env} metrics=:{metrics_port} symbol={jit['symbol']} (Enhanced Mock)")
    signal.signal(signal.SIGINT, _sigterm)
    signal.signal(signal.SIGTERM, _sigterm)

    spread_bps = float(jit["spread_bps"]["base"])
    post_only = bool(jit.get("post_only", True))

    # Enhanced main loop with realistic market making
    while RUNNING:
        try:
            # Get current orderbook
            ob = client.get_orderbook()
            if not ob.bids or not ob.asks:
                print("[JIT] No orderbook data, skipping iteration")
                time.sleep(1.0)
                continue
                
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
            
            # Calculate bid/ask prices with spread
            bid = mid * (1 - spread_bps/2/10000)
            ask = mid * (1 + spread_bps/2/10000)
            
            # Place realistic market making orders
            # Use larger sizes and more aggressive pricing to increase fill probability
            bid_order = Order(
                side=OrderSide.BUY,
                price=round(bid, 4),
                size_usd=50.0  # Increased from 0.01 to make orders more likely to fill
            )
            
            ask_order = Order(
                side=OrderSide.SELL,
                price=round(ask, 4),
                size_usd=50.0  # Increased from 0.01 to make orders more likely to fill
            )
            
            # Place orders
            bid_id = client.place_order(bid_order)
            ask_id = client.place_order(ask_order)
            
            print(f"[JIT] Placed orders: BUY {bid_order.size_usd:.1f} @ ${bid_order.price:.4f} | SELL {ask_order.size_usd:.1f} @ ${ask_order.price:.4f}")
            
            quotes_c.inc(2)
            spread_g.set(spread_bps)
            
            # Check for fills and update metrics
            trades = client.get_trade_history()
            if len(trades) > prints_c._value.get():
                prints_c.inc(len(trades) - prints_c._value.get())
            
            # Show current PnL
            pnl_summary = client.get_pnl_summary()
            positions = client.get_positions()
            
            if positions:
                for market, pos in positions.items():
                    if pos.size != 0:
                        print(f"[JIT] Position: {pos.size:+.4f} SOL @ ${pos.avg_price:.4f} | PnL: ${pos.unrealized_pnl:+.2f}")
            
            time.sleep(2.0)  # Increased from 1.0 to give more time for fills
            
        except Exception as e:
            print(f"[JIT] Error in main loop: {e}")
            time.sleep(1.0)

    print("[JIT] graceful shutdown")
    await client.close()
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
