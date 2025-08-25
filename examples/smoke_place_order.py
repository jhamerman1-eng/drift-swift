import os, time
from libs.drift.client import ClientFactory

# Ensure env is loaded before running:
# RPC_URL, WS_URL, SOLANA_CLUSTER=devnet, SWIFT_SIDECAR_PORT=8787

c = ClientFactory.from_env()
print("Health:", c.health())

# Place a tiny post-only bid
resp = c.place_order(marketIndex=0, price=135.25, size=0.02, postOnly=True, side='bid')
print("Place resp:", resp)
