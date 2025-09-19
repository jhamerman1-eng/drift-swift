Swift Sidecar Testing Guide

Overview
- Provides unit tests for Swift envelope creation (validation, format, breaker)
- Provides simple integration tests against the local Swift sidecar stub

Prerequisites
- Python 3.10+
- Packages: pytest, httpx, solders, driftpy (already used by the repo)
- Sidecar running locally on http://localhost:8787

Start the Sidecar
- Option A: Docker
  - docker-compose -f docker-compose.swift.yml up -d
- Option B: Node dev server
  - cd services/swift-mm
  - npm install
  - npm run dev

Run Tests
- From repo root:
  - pytest -q tests/test_swift_envelope.py
  - pytest -q tests/test_swift_sidecar_contract.py  # skipped if sidecar not running

Format Toggle
- The envelope format can be toggled via env var:
  - SWIFT_ENVELOPE_FORMAT=base64  (default)
  - SWIFT_ENVELOPE_FORMAT=raw     (legacy/raw JSON)

Circuit Breaker Tuning
- Consecutive failure threshold is controlled by:
  - SWIFT_ENVELOPE_MAX_FAILS (default: 5)

Notes
- The sidecar stub accepts any JSON in /orders and returns {ok: true}; the integration
  tests verify reachability and that both envelope formats are accepted at the transport layer.
- Against a strict forwarder, keep SWIFT_ENVELOPE_FORMAT aligned with its expectations.

