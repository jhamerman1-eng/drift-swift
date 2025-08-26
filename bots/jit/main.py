from __future__ import annotations
import argparse
import os
import signal
import sys
import time
import yaml
from pathlib import Path
from prometheus_client import start_http_server, Gauge, Counter

# Local import
from libs.drift.client import DriftClient

RUNNING = True

def _sigterm(_signo, _frame):
    global RUNNING
    RUNNING = False

def load_yaml(path: Path) -> dict:
    with path.open("r") as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description="JIT Maker Bot (scaffold)")
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

    # Client
    client = DriftClient(core)
    client.connect()

    print(f"[JIT] env={args.env} metrics=:{metrics_port} symbol={jit['symbol']} (stub loop)")
    signal.signal(signal.SIGINT, _sigterm)
    signal.signal(signal.SIGTERM, _sigterm)

    spread_bps = float(jit["spread_bps"]["base"])
    post_only = bool(jit.get("post_only", True))

    # Stub main loop
    while RUNNING:
        ob = client.get_orderbook(jit["symbol"])
        mid = (ob["bids"][0][0] + ob["asks"][0][0]) / 2.0
        bid = mid * (1 - spread_bps/2/10000)
        ask = mid * (1 + spread_bps/2/10000)

        # Place stub quotes
        client.place_order(jit["symbol"], "buy", round(bid, 4), 0.01, post_only=post_only)
        client.place_order(jit["symbol"], "sell", round(ask, 4), 0.01, post_only=post_only)

        quotes_c.inc(2)
        spread_g.set(spread_bps)
        time.sleep(1.0)

    print("[JIT] graceful shutdown")
    sys.exit(0)

if __name__ == "__main__":
    main()
