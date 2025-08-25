# Changelog

## v0.9.1 — Swift Sidecar Integration (Devnet)

**What’s new**
- Added Swift MM sidecar (`services/swift-mm/`) and Python adapter (`libs/drift/client.py`) — driver now defaults to `swift`.
- Devnet-ready `.env.example` with Helius RPC & WS placeholders.
- Prometheus metrics at `:8787/metrics` and HTTP health at `POST /health`.
- New RPC connectivity smoke scripts.

**Why this matters**
- Moves quoting path off AnchorPy → lower latency & simpler reconnects.
- Keeps Python orchestrator unchanged via an HTTP adapter.
- Sets us up for mainnet cutover with minimal changes (switch RPC and cluster).

**Upgrade steps**
1) Merge the sidecar & adapter.
2) Copy `.env.v9.1.devnet` to `.env` (or paste values into your existing `.env`).
3) `cd services/swift-mm && npm i && npm run dev`
4) Run `python scripts/rpc_test.py` to verify RPC, then `python examples/smoke_place_order.py`.

