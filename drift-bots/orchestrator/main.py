import argparse
import asyncio
import os
from loguru import logger
from libs.metrics import start_metrics
from bots.jit.main import run as run_jit
from bots.hedge.main import run as run_hedge
from bots.trend.main import run as run_trend

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.getenv("DRIFT_ENV", "testnet"))
    parser.add_argument("--metrics-port", type=int, default=int(os.getenv("METRICS_PORT", 9100)))
    args = parser.parse_args()

    start_metrics(args.metrics_port)
    logger.info(f"Orchestrator starting on {args.env} – metrics @ {args.metrics_port}")

    # Launch all three bots concurrently
    await asyncio.gather(
        run_jit(env=args.env, metrics_port=None),
        run_hedge(env=args.env, metrics_port=None),
        run_trend(env=args.env, metrics_port=None),
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Orchestrator shutdown")
