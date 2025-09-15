Swift WS Integration Reference (Drift Labs)

This document preserves the canonical TypeScript example for Swift WebSocket integration and maps it to the Python implementation in this repository.

Key Concepts
- Transport: WebSocket, not HTTP for receiving orders.
- Auth: Connect with delegate pubkey in the query string; respond to a nonce challenge signed with the delegate secret key.
- Orders: Received over WS as signed messages (order_message hex + order_signature base64). Use Drift client helpers to decode and place/make.

Reference (TypeScript)
```ts
// (verbatim excerpt for future reference)
// Paste your TS example here when needed
```

Python Implementation in This Repo
- Official subscriber: `run_mm_bot_swift_official.py`
  - Uses `driftpy.swift.order_subscriber.SwiftOrderSubscriber` to subscribe to Swift orders over WS.
  - Handles auth, subscribe, decoding, and provides hooks to act on incoming orders.

Manual Compatibility Layer
- Envelope generator (for manual HTTP fallback): `libs/drift/swift_envelope.py`
  - Defaults: SWIFT_ENVELOPE_FORMAT=hex, SWIFT_ENVELOPE_FIELDS=hexcompat (signedMessage + signature (hex), marketIndex, marketType, takerAuthority, publicKey)
  - Retry-on-422 with base64 + standard for sidecar variants (when using manual HTTP path).

Operational Notes
- RPC/wallet are centralized via `orchestrator/env_loader.py`; all bots share the same configuration.
- Orchestrator places a tiny smoke trade per role on startup to validate chain visibility before MM starts.
- If Swift ever returns 422 on manual paths, see `docs/SWIFT_422_INVALID_SIGNED_MESSAGE.md`.

Going Live
- Devnet: DRIFT_ENV=devnet; confirm wallet funded.
- Mainnet/Beta: switch RPC and cluster; ensure sidecar auth (SWIFT_API_KEY) if required.
