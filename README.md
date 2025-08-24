# Drift Bots — Sprint 0 (Core Infra)

This repository delivers **Sprint 0**: a production‑ready core in Python for:

- **Drift Client Wrapper** (REST + WebSocket, retries, rate limiting, nonce management, metrics)
- **Orchestrator** (supervisor loop, feature flags, risk rails, circuit breaker, kill switch)
- **Configs + Tests** (sane defaults, edge‑case test stubs)

> Language: **Python 3.11+** (async‑first)

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set env for signer (example only; wire actual Drift creds)
export DRIFT_API_KEY="xxx"
export DRIFT_API_SECRET="yyy"

# Run orchestrator with JIT stub
python -m orchestrator.run
```

## Layout

```
libs/drift_client/     # Client wrapper
orchestrator/          # Supervisor + strategies
configs/               # YAML configs
tests/                 # Unit + integration stubs
```

## Notes

- REST/WS endpoints are placeholders; wire to the actual Drift endpoints/headers.
- `Signer` exposes pluggable providers; replace with a real signing scheme.
- Circuit breaker & rate limiter are framework‑agnostic.
- Keep Sprint 0 scope: JIT stub only (no live trading logic).
