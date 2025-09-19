# v1.17.0-RC — Merged Library (Improved)

This archive merges the v9.1 operator pack with a heavily
extended version of the v16.9 functional baseline.  The goal of
v1.17.0‑RC is to transform the original skeleton into a more
complete, testable framework that can serve as the foundation for a
production market‑making stack.

## Highlights

- **Asynchronous Drift client** (`libs/drift/client.py`)
  - Implements an async HTTP/WebSocket client with rate limiting,
    connection pooling and automatic orderbook subscriptions.
  - Includes a mock implementation for offline development and a
    stub for integrating the official `driftpy` library.
- **Order & position tracking** (`libs/order_management.py`)
  - Provides a `PositionTracker` to keep track of net long/short
    exposure and traded volume.
  - Adds an `OrderManager` to record open orders by ID.
- **Enhanced risk management**
  - `libs/risk/crash_detector.py` now implements a rolling sigma
    detector with configurable thresholds and cool‑off.
  - `orchestrator/risk_manager.py` tracks peak equity internally and
    returns explicit trading permissions (allow/trend/pause).
- **JIT bot overhaul** (`bots/jit/main.py`)
  - Fetches orderbooks via the new client, computes quotes, consults
    the risk manager, records orders and updates exposure.
  - Supports graceful shutdown and cleans up network resources.
- **Config improvements** (`configs/core/drift_client.yaml`)
  - Adds `env`, `market`, `use_mock`, `rpc_url` and `ws_url` keys
    recognised by the client builder.
  - Retains legacy keys for backwards compatibility with earlier
    operator tooling.

## Structure
- `.env.example` / `README-operator.md` — operator runbook & env template
- `configs/` — YAML stubs for risk, hedge, trend, OBI; improved drift client config
- `libs/` — crash detector, order management and async drift client
- `orchestrator/` — improved risk manager
- `bots/` — updated JIT bot and stubs for hedge/trend
- `tests/` — minimal placeholder tests; expand with your own fixtures
- `regression/` — regression harness placeholders

## Remaining work

- Complete the `DriftpyClient` implementation once the official
  library is available and configured.
- Implement real order sizing, orderbook maintenance and fill
  handling.  The current implementation assumes immediate fills and
  does not react to fills.
- Flesh out hedge and trend bots using the new client and risk
  primitives.
- Tune configuration parameters (spreads, hedge routing, risk rails)
  for your environment.
- Replace mock clients with connections to your actual infrastructure.
- Expand unit and regression tests with realistic scenarios and
  performance benchmarks.

This version provides a significantly more functional base than the
earlier stub.  It is by no means complete, but it establishes the
architecture and patterns necessary for building out a robust trading
system.
