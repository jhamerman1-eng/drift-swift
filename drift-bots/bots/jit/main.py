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

    try:
        while True:
            t0 = time.perf_counter()
            # Use the wrapper's orderbook. Mock client synthesizes one.
            ob = client.get_orderbook()
            if not ob.bids or not ob.asks:
                await asyncio.sleep(0.05)
                continue
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
            record_mid(mid)

            spread = jit["spread_bps"] / 10000.0 * mid
            bid = mid - spread / 2
            ask = mid + spread / 2
            size = float(jit["quote_size_usd"])  # USD notional (mock sizing)

            _ = client.place_order(Order(side="buy", price=bid, size_usd=size))
            _ = client.place_order(Order(side="sell", price=ask, size_usd=size))
            ORDERS_PLACED.inc(2)

            INV_USD.set(0.0)  # placeholder; wire real inventory later
            LOOP_LATENCY.observe(time.perf_counter() - t0)
            await asyncio.sleep(jit["refresh_ms"] / 1000.0)
    finally:
        close = getattr(client, "close", None)
        if asyncio.iscoroutinefunction(close):
            await close()  # type: ignore

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