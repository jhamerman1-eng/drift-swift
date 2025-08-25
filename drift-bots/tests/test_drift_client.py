import os
import asyncio
from libs.drift.client import build_client_from_config

async def _build_and_fetch():
    client = await build_client_from_config(os.getenv("DRIFT_CFG", "configs/core/drift_client.yaml"))
    ob = client.get_orderbook()
    assert hasattr(ob, "bids") and hasattr(ob, "asks")

def test_build_and_orderbook():
    asyncio.run(_build_and_fetch())