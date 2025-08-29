import asyncio
import os
from driftpy.drift_client import DriftClient
from driftpy.addresses import PerpMarketIndex
from driftpy.types import PositionDirection
from libs.drift.swift_submit import swift_market_taker

# Env to set before running:
#   KEYPAIR_PATH=C:\path\to\maker-keypair.json
#   DRIFT_CLUSTER=beta  (beta uses real SOL)
# Optional:
#   SWIFT_BASE=https://swift.drift.trade

async def main():
    # Small position to prove-through
    market_index = int(os.getenv("MARKET_INDEX", PerpMarketIndex.SOL))  # 0 by default
    qty = float(os.getenv("TEST_QTY", "0.01"))  # 0.01 SOL
    direction = PositionDirection.Long()        # or PositionDirection.Short()

    client = await DriftClient.connect()
    try:
        resp = await swift_market_taker(
            client,
            market_index=market_index,
            direction=direction,
            qty_perp=qty,
        )
        print("✅ Swift order accepted:", resp)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())