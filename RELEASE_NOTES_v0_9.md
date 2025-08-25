# v0.9.0 — Relink & Git Update Package

**Date:** 2025-08-25  
**Scope:** Relink repo to v0.9, add minimal Drift client wiring, JIT bot entrypoint, configs, tests, and metrics.

## What’s in this package
- `apply_patch.sh` — copies `files/` into your repo, commits on a `release/v0.9` branch, and tags `v0.9.0`.
- `relink_v0_9.sh` — optional helper to set origin (or a new remote) and push the tag/branch.
- `files/` — drop-in tree with:
  - `VERSION` set to `0.9.0`
  - `libs/drift/client.py` (driftpy/anchorpy-based wrapper; safe stubs if libs missing)
  - `bots/jit/main.py` (metrics server + skeleton JIT loop)
  - `configs/core/drift_client.yaml` (RPC/WS/wallet config with env interpolation)
  - `.env.example` (placeholders)
  - `scripts/seed_flags.py` (seed local feature flags for dev)
  - `tests/test_drift_client.py` (smoke test)
  - `Makefile`, `pyproject.toml`, `requirements.txt`
  - `README_v0_9.md` (how to run locally)
  
## Quick Use
1. Unzip at the **root of your repo**.
2. Run: `bash apply_patch.sh`
3. Optional: `bash relink_v0_9.sh <git-remote-url>`
4. Push: `git push origin release/v0.9 --tags`

## Notes
- Safe to run on an empty repo **or** an existing tree (it only adds/updates these specific files).
- No secrets included; use `.env` based on `.env.example`.
- Minimal Fast metrics via Prometheus client on port `9108` by default.
