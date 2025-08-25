import argparse
import asyncio
import os
import time
import yaml
from pathlib import Path
from loguru import logger
from libs.metrics import start_metrics, LOOP_LATENCY, ORDERS_PLACED
from libs.drift.client import build_client_from_config

HEDGE_CFG = Path("configs/hedge/routing.yaml")
CORE_CFG = os.getenv("DRIFT_CFG", "configs/core/drift_client.yaml")

async def run(env: str = "testnet", metrics_port: int | None = 9102, cfg_path: str = CORE_CFG):
    if metrics_port:
        start_metrics(metrics_port)
    hed = yaml.safe_load(Path(HEDGE_CFG).read_text())["hedge"]
    client = await build_client_from_config(cfg_path)
    logger.info(f"Hedge bot (mode={hed['mode']}) starting – env={env}")

    try:
        while True:
            t0 = time.perf_counter()
            # In v0.2 we only log hedge intents (stub)
            urgency = 0.5  # placeholder scoring
            route = "ioc" if urgency >= hed["urgency_threshold"] else "passive"
            logger.info(f"[HEDGE] intent: urgency={urgency:.2f} → route={route}")
            ORDERS_PLACED.inc()
            LOOP_LATENCY.observe(time.perf_counter() - t0)
            await asyncio.sleep(2.0)
    finally:
        close = getattr(client, "close", None)
        if asyncio.iscoroutinefunction(close):
            await close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.getenv("DRIFT_ENV", "testnet"))
    parser.add_argument("--metrics-port", type=int, default=9102)
    parser.add_argument("--cfg", default=CORE_CFG)
    args = parser.parse_args()
    try:
        asyncio.run(run(env=args.env, metrics_port=args.metrics_port, cfg_path=args.cfg))
    except KeyboardInterrupt:
        logger.info("Hedge bot shutdown")