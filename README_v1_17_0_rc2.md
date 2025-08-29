# driftbot v1.17.0-rc2 (Release Candidate 2)

This is a ready-to-drop scaffold that merges the v0.9.x Swift sidecar approach with the 1.16.x Python bot tree.
It includes:
- Python JIT bot entrypoint with Prometheus `/metrics`
- Swift sidecar folder (TypeScript) + Dockerfile + docker-compose.swift.yml
- Configs for Drift client, JIT params, risk, hedging, trend, and OBI weights
- Tests and a tag script to mark this RC in your repo

## Quick Start
1) Unzip this archive into your repo root.
2) Create a virtualenv and install deps:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   make install
   ```
3) Copy `.env.example` to `.env` and fill values.
4) Run the JIT bot scaffold (testnet placeholder, metrics on :9300):
   ```bash
   make run
   ```
5) (Optional) Build & run the Swift sidecar:
   ```bash
   docker compose -f docker-compose.swift.yml up --build
   ```
6) Tag this RC in Git:
   ```bash
   make tag
   ```

**Note:** Integration calls are stubbed. Wire `libs/drift/client.py` to DriftPy or to the Swift sidecar HTTP/WebSocket when you are ready.
