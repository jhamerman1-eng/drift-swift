# v0.9.1 Release Notes — Swift MM Integration (Devnet)

**Owner:** PM/Trading (Jeremy)  
**Date:** [Today]

### Summary
- Introduces Swift MM sidecar with Drift SDK, default driver set to `swift`.
- Keeps Python orchestrator API intact via HTTP adapter.
- Adds RPC smoke testing and a devnet `.env` with Helius endpoints.

### Acceptance
- `/health` returns `{ ok: true, driver: 'swift' }`
- `scripts/rpc_test.py` returns version + slot without error.
- `examples/smoke_place_order.py` submits a post-only order on SOL-PERP (devnet).

### Next
- Replace tick/lot helpers with on-chain metadata mapping.
- Add cancel/replace atomic flow and hedging hooks.
- Prep mainnet cutover runbook.
