# v1.17.0-RC — Merged Library (Stubbed)

This archive merges:
- v9.1 operator pack (env + runbook polish)
- v16.9 functional baseline (bots + risk + configs)

## Structure
- `.env.example` / `README-operator.md` — operator runbook & env template
- `configs/` — YAML stubs for risk, hedge, trend, OBI
- `libs/` — stub crash detector
- `orchestrator/` — stub risk manager
- `bots/` — JIT, Hedge, Trend stub code
- `tests/` — minimal placeholder tests

## What is stubbed (needs implementation)
- All functions contain `TODO` markers (logic from actual repo required)
- Smoke test (`scripts/rpc_smoketest.py`) simplified; replace with full connectivity checker
- Regression tests are placeholders

## What to update
- Fill configs with production-ready parameters
- Implement bot logic (JIT quoting, hedge execution, trend entries)
- Flesh out risk management (Crash Sentinel v2, portfolio rails)
- Add proper regression pack test cases

This provides a working skeleton your devs can immediately build upon.
