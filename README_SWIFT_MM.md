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
