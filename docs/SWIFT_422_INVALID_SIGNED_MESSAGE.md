Swift 422 “invalid signed message hex” — Resolution Guide

Overview
- This error comes from the Swift sidecar when it cannot parse the order’s signed message fields.
- Root causes are almost always field naming or encoding mismatches.

Recommended Defaults (already set in code)
- SWIFT_ENVELOPE_FORMAT=hex
- SWIFT_ENVELOPE_FIELDS=hexcompat
Produces:
- signedMessage: hex-encoded message bytes
- signature: hex-encoded Ed25519 signature
- marketIndex, marketType, takerAuthority, publicKey

Quick Fix Steps
1) Confirm sidecar health:
   curl -sS $SWIFT_SIDECAR_URL/health
   (or /ready, /v1/health, /status)

2) Ensure the envelope defaults are active (no env needed; code defaults to hex/hexcompat).
   To override manually:
   - Windows: set SWIFT_ENVELOPE_FORMAT=hex & set SWIFT_ENVELOPE_FIELDS=hexcompat
   - Linux/macOS: export SWIFT_ENVELOPE_FORMAT=hex; export SWIFT_ENVELOPE_FIELDS=hexcompat

3) Check the payload printed before POST /orders in run_swift_mm_complete logs.
   - You should see signedMessage and signature as hex strings.

4) If 422 persists, the code will retry once with base64/standard keys.
   - Look for “Alt Swift payload” and the retry result.

5) Wallet format:
   - The maker keypair is a JSON array of 64 ints or a b58 string of 64 bytes. The code handles both.
   - Do not paste private keys in configs directly; point configs/core/drift_client.yaml wallets.maker_keypair_path to the local file.

6) Drift UI confirmation (Devnet):
   - Orchestrator posts a tiny smoke trade for each role on startup.
   - Set UI to Devnet and connect the same wallet (DRIFT_KEYPAIR_PATH). You should see smoke trades immediately.

What to Collect If It Still Fails
- The 422 response body text (printed in logs).
- The printed payload JSON (Swift payload) and the message key/format.
- Your sidecar’s expected schema (if it differs). We can add a new profile toggle to match it exactly.

Prevention
- Defaults set to hex/hexcompat to match typical Swift sidecars.
- Automatic one-time retry with base64/standard on 422.
- Logging of both payload and message key/format to speed diagnosis.
- Orchestrator-side smoke trades to verify environment and wallet setup.

Related files
- libs/drift/swift_envelope.py: Envelope generation (format/field profiles)
- run_swift_mm_complete.py: Manual Swift path; logs payload and retries on 422
- run_mm_bot_swift_official.py: Official integration via SwiftOrderSubscriber (no manual payloads)
- orchestrator/master.py: Subprocess launcher, smoke trades, health/metrics

