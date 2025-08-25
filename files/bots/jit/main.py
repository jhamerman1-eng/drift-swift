"""
v0.9 JIT Bot entrypoint.
- Starts a Prometheus metrics server on METRICS_PORT (env or --metrics-port).
- Wires a skeleton Drift client loop (no live orders by default).
"""
import argparse
import asyncio
import os
import time
from prometheus_client import start_http_server, Counter, Gauge

from libs.drift.client import DriftClient, DriftConfig

TICK_QUOTE_LATENCY_MS = Gauge("tick_to_quote_latency_ms", "p50/p99 tick->quote latency (simulated)")
BOT_HEARTBEAT = Counter("bot_heartbeat", "JIT bot heartbeats")

async def jit_loop(client: DriftClient):
    # Placeholder: increment heartbeat and set a fake latency
    while True:
        BOT_HEARTBEAT.inc()
        TICK_QUOTE_LATENCY_MS.set(15.0)
        await asyncio.sleep(5)

def load_cfg(args) -> DriftConfig:
    return DriftConfig(
        rpc_url=os.getenv("DRIFT_RPC_URL", "https://api.testnet.solana.com"),
        ws_url=os.getenv("DRIFT_WS_URL"),
        wallet_path=os.getenv("WALLET_PATH", os.path.expanduser("~/.config/solana/id.json")),
        env=args.env,
        market=os.getenv("DEFAULT_MARKET", "SOL-PERP"),
    )

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default="testnet", choices=["testnet", "mainnet"])
    parser.add_argument("--metrics-port", type=int, default=int(os.getenv("METRICS_PORT", "9108")))
    args = parser.parse_args()

    start_http_server(args.metrics_port)
    cfg = load_cfg(args)
    client = DriftClient(cfg)

    try:
        # Connect only if driftpy present; otherwise runs in dry mode
        try:
            await client.connect()
            print("[v0.9] Connected to Drift")
        except Exception as e:
            print(f"[v0.9] Drift connect skipped/failed (dry mode): {e}")

        await jit_loop(client)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            await client.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
