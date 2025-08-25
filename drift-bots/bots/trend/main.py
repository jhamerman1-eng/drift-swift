import argparse
import asyncio
import os
import time
import yaml
from pathlib import Path
from collections import deque
from loguru import logger
from libs.metrics import start_metrics, LOOP_LATENCY, ORDERS_PLACED
from libs.drift.client import build_client_from_config

TREND_CFG = Path("configs/trend/filters.yaml")
CORE_CFG = os.getenv("DRIFT_CFG", "configs/core/drift_client.yaml")

def macd(prices: list[float], fast: int, slow: int, signal: int) -> tuple[float, float]:
    def ema(vals, n):
        k = 2 / (n + 1)
        e = vals[0]
        out = []
        for v in vals:
            e = v * k + e * (1 - k)
            out.append(e)
        return out
    if len(prices) < slow + signal:
        return 0.0, 0.0
    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)
    # Align to same length
    length = min(len(fast_ema), len(slow_ema))
    macd_line = [fast_ema[-length + i] - slow_ema[i] for i in range(length)]
    sig_line = ema(macd_line, signal)
    return macd_line[-1], sig_line[-1]

async def run(env: str = "testnet", metrics_port: int | None = 9103, cfg_path: str = CORE_CFG):
    if metrics_port:
        start_metrics(metrics_port)
    cfg = yaml.safe_load(Path(TREND_CFG).read_text())["trend"]
    client = await build_client_from_config(cfg_path)
    prices: deque[float] = deque(maxlen=500)
    logger.info(f"Trend bot starting – env={env}")
    try:
        while True:
            t0 = time.perf_counter()
            ob = client.get_orderbook()
            if ob.bids and ob.asks:
                mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
                prices.append(mid)
                trade_signal = None
                if cfg.get("use_macd", True):
                    m, s = macd(list(prices), cfg["macd"]["fast"], cfg["macd"]["slow"], cfg["macd"]["signal"])
                    if m > s:
                        trade_signal = "long"
                    elif m < s:
                        trade_signal = "short"
                if trade_signal:
                    logger.info(f"[TREND] signal={trade_signal} @ mid={mid:.2f}")
                    ORDERS_PLACED.inc()
            LOOP_LATENCY.observe(time.perf_counter() - t0)
            await asyncio.sleep(1.0)
    finally:
        close = getattr(client, "close", None)
        if asyncio.iscoroutinefunction(close):
            await close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.getenv("DRIFT_ENV", "testnet"))
    parser.add_argument("--metrics-port", type=int, default=9103)
    parser.add_argument("--cfg", default=CORE_CFG)
    args = parser.parse_args()
    try:
        asyncio.run(run(env=args.env, metrics_port=args.metrics_port, cfg_path=args.cfg))
    except KeyboardInterrupt:
        logger.info("Trend bot shutdown")