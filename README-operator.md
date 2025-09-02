# Operator README (v1.17.0-RC)
1) Copy `.env.example` → `.env`, fill real values.
2) Ensure keypair paths are absolute and valid JSON arrays.
3) `pip install websockets` (optional), then `python scripts/rpc_smoketest.py --env-file .env`.
4) Point bots to `configs/core/drift_client.yaml`. Expose `/metrics` on `$METRICS_PORT`.
