#!/usr/bin/env python3
"""
Simple integration tests for the Swift sidecar HTTP contract.

These tests assume a sidecar is running locally on http://localhost:8787
(you can start it via `docker-compose -f docker-compose.swift.yml up -d`
or `npm --prefix services/swift-mm run dev`).

Tests are skipped if the sidecar is not reachable.
"""

import os
import json
import httpx
import pytest
import base64

from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
from solders.keypair import Keypair


BASE = os.getenv("SWIFT_SIDECAR_URL", "http://localhost:8787")


def sidecar_available() -> bool:
    try:
        r = httpx.get(f"{BASE}/health", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not sidecar_available(), reason="Swift sidecar not running")


def _make_env(fmt: str) -> dict:
    os.environ["SWIFT_ENVELOPE_FORMAT"] = fmt
    kp = Keypair()
    params = SwiftOrderParams(
        market_index=0,
        market_type="perp",
        side="buy",
        price=100.0,
        size=0.01,
        taker_authority=str(kp.pubkey()),
    )
    env = SwiftEnvelopeCreator().create_order_envelope(params, kp)
    return env


def _post_order(envelope: dict) -> httpx.Response:
    return httpx.post(f"{BASE}/orders", json=envelope, timeout=2.0)


def test_health_endpoint():
    r = httpx.get(f"{BASE}/health", timeout=1.0)
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True or "ts" in body


def test_place_order_base64():
    env = _make_env("base64")
    r = _post_order(env)
    assert r.status_code == 200
    body = r.json()
    # Local stub returns { ok: true }
    assert body.get("ok") is True or body.get("status") in ("accepted", "ok", "success")
    if body.get("id"):
      rs = httpx.get(f"{BASE}/orders/{body['id']}/status", timeout=2.0)
      assert rs.status_code in (200, 404)


def test_place_order_raw():
    env = _make_env("raw")
    r = _post_order(env)
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True or body.get("status") in ("accepted", "ok", "success")
    if body.get("id"):
      rs = httpx.get(f"{BASE}/orders/{body['id']}/status", timeout=2.0)
      assert rs.status_code in (200, 404)
