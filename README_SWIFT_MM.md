# Swift MM Sidecar & Python Driver

This adds a Node/TypeScript **Swift MM Sidecar** and a Python **SwiftSidecarDriver**.

## Why
- Avoids 422 signature/encoding issues by keeping signing in Python and forwarding envelopes.
- Provides a **local ACK mode** for offline smoke tests.
- When `SWIFT_FORWARD_BASE` is set, the sidecar **proxies** to the real Swift API.
- Exposes `/health`, `/metrics`, `/orders` (submit), and `/orders/:id/cancel`.

## Layout
```
services/swift-mm/
  Dockerfile
  package.json
  tsconfig.json
  src/
    index.ts
    metrics.ts
    types.ts
libs/drift/swift_sidecar_driver.py
docker-compose.swift.yml
configs/core/swift_mm.example.env
examples/swift_smoke_place_order.py
```

## Quick start
```bash
cp configs/core/swift_mm.example.env .env.swift
docker compose -f docker-compose.swift.yml --env-file .env.swift up -d --build
curl -s localhost:8787/health
curl -s localhost:8787/metrics | head
```

## Using the Python driver
```python
from libs.drift.swift_sidecar_driver import SwiftSidecarDriver
driver = SwiftSidecarDriver(base_url="http://localhost:8787", api_key=None)
ack = driver.place_order({
    "message": "SignedMsgOrderParamsMessageBase64OrHex",
    "signature": "base64/hex",
    "market_index": 0,
    "market_type": "perp",
    "taker_authority": "yourPubkey",
})
print(ack)
```

To cancel:
```python
driver.cancel_order("your-order-id")
```

## Modes
- **Local ACK mode** (default): sidecar returns `{"status":"accepted","id":"..."}`
- **Forward mode**: set `SWIFT_FORWARD_BASE` to the real Swift base (e.g. `https://swift.drift.trade`)

## Env (example)
See `configs/core/swift_mm.example.env`.

## Metrics
Prometheus endpoint at `/metrics`. Basic counters/timers are included:
- `swift_submit_seconds` (histogram)
- `swift_submit_total`
- `swift_cancel_seconds` (histogram)
- `swift_cancel_total`

## Notes
- Keep secrets out of the repo and environment where possible.
- Start with tiny order sizes on devnet/beta to validate wiring.