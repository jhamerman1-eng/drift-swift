import argparse
import asyncio
import os
import time
from pathlib import Path
import yaml
from loguru import logger

from libs.metrics import start_metrics, LOOP_LATENCY, ORDERS_PLACED, record_mid, INV_USD
from libs.drift.client import build_client_from_config, Order

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
        close = getattr(client, "close", None)
        if asyncio.iscoroutinefunction(close):
            await close()  # type: ignore
        elif callable(close):
            close()
        logger.info("JIT Maker shutdown complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.getenv("DRIFT_ENV", "testnet"))
    parser.add_argument("--metrics-port", type=int, default=9101)
    parser.add_argument("--cfg", default=CORE_CFG)
    args = parser.parse_args()

    try:
        asyncio.run(run(env=args.env, metrics_port=args.metrics_port, cfg_path=args.cfg))
    except KeyboardInterrupt:
        logger.info("JIT Maker shutdown")