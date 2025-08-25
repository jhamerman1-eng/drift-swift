# Swift MM Sidecar Scaffold (Devnet-ready)

This package drops a **Swift/Drift SDK sidecar** next to your Python bots. Your Python orchestrator
calls a tiny HTTP API (`/place`, `/cancelReplace`, `/health`, `/metrics`) and the sidecar pushes
orders via the Drift SDK (Swift-backed infra).

## Quick start

1) Copy files into your repo (keep paths the same).
2) Create a `.env` from `.env.example` and paste your **Helius devnet** RPC + WS URLs.
3) Start the sidecar:

```bash
cd services/swift-mm
npm i
npm run dev
```

4) From Python, set `DRIVER=swift` (or keep config default) and call the client.

```python
from libs.drift.client import ClientFactory
c = ClientFactory.from_env()
print(c.health())
print(c.place_order(marketIndex=0, price=135.25, size=0.02, postOnly=True, side='bid'))
```

5) Metrics are exposed at `http://127.0.0.1:8787/metrics` (Prometheus text format).

## Notes

- This scaffold includes **auth (optional)** for the sidecar (`SWIFT_API_KEY`), **Prometheus metrics**,
  and **tick/lot math helpers** with safe fallbacks to env overrides if market introspection fails.
- For **mainnet**, update `SOLANA_CLUSTER=mainnet-beta` and swap RPC/WS to mainnet endpoints.
- Replace the placeholder lot/tick conversions with your exact market metadata when you wire live.

