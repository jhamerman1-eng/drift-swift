# Swift MM Sidecar (Scaffold)

A minimal TypeScript service that would sit between the Python bot and Drift Swift components.
This version exposes `/health`, `/metrics`, simple market data, and stubs for order relaying and a WS endpoint.

## Dev
```bash
cd services/swift-mm
npm install
npm run build
node dist/index.js
```

Or via Docker:
```bash
docker build -t swift-mm:rc2 .
docker run -p 8787:8787 swift-mm:rc2
```

### HTTP endpoints

- `GET /health` – basic health check
- `GET /metrics` – Prometheus metrics
- `GET /markets/:symbol` – fetch stubbed order book for a symbol
- `POST /orders` – submit a stub order `{symbol, side, price, size}`

WebSocket clients may connect to `/ws` to experiment with message relays.

## Python Swift Integration

The Python bots now support direct Swift integration for high-speed market taker orders:

### Features
- **High-speed execution** via Swift's optimized matching engine
- **Market taker orders** with auction pricing
- **Real-time market data** from Drift protocol
- **Direct blockchain settlement** on Solana

### Usage

```python
from libs.drift.swift_submit import swift_market_taker
from driftpy.types import PositionDirection

# Place a market buy order
result = await swift_market_taker(
    drift_client=client.drift_client,
    market_index=0,  # SOL-PERP
    direction=PositionDirection.Long(),
    qty_perp=0.1,   # 0.1 SOL
    auction_ms=50    # Auction duration
)
```

### Example
See `examples/swift_market_taker_example.py` for a complete working example.

### Requirements
- `driftpy` package installed
- Valid Solana wallet with DEV SOL
- Drift account initialized
- Swift API access (configured via `SWIFT_BASE` environment variable)

### Environment Variables
```bash
SWIFT_BASE=https://swift.drift.trade  # Swift API endpoint
DRIFT_RPC_URL=https://api.devnet.solana.com  # Solana RPC
DRIFT_WS_URL=wss://api.devnet.solana.com     # Solana WebSocket
KEYPAIR_PATH=.beta_dev_wallet.json            # Your wallet
```

This integration enables **sub-millisecond order execution** for high-frequency trading strategies!