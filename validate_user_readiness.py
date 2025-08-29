#!/usr/bin/env python3
"""
User Readiness Smoke Test
Validates that the Drift client can initialize user account and subscriber properly.
"""
import asyncio
import yaml
import json
from libs.drift.client import DriftpyClient

async def main():
    cfg = yaml.safe_load(open("configs/core/drift_client.yaml"))

    # Read and parse wallet as JSON array, then convert to bytes
    with open(cfg["wallets"]["maker_keypair_path"], 'r') as f:
        wallet_data = json.load(f)

    # Convert JSON array to bytes
    wallet_bytes = bytes(wallet_data)

    c = DriftpyClient(
        rpc_url=cfg["rpc"]["http_url"],
        wallet_secret_key=wallet_bytes,
        market=cfg.get("market","SOL-PERP"),
        ws_url=cfg["rpc"]["ws_url"],
        use_fallback=True
    )
    # Connect first, then ensure user ready
    await c.connect()
    await c._ensure_user_ready(0)
    print("✅ OK: user ready - account initialized and subscriber active")

if __name__ == "__main__":
    asyncio.run(main())
