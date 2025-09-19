#!/usr/bin/env python3
"""
Unit tests for SwiftEnvelopeCreator covering:
- Raw vs base64 message formats
- Field validation
- Circuit breaker behavior
"""

import os
import json
import base64
import pytest

from libs.drift.swift_envelope import (
    SwiftEnvelopeCreator,
    SwiftOrderParams,
    CriticalSignatureError,
    CircuitBreakerOpen,
)
from solders.keypair import Keypair


def make_params() -> SwiftOrderParams:
    return SwiftOrderParams(
        market_index=0,
        market_type="perp",
        side="buy",
        price=100.0,
        size=0.01,
        taker_authority=str(Keypair().pubkey()),
        sub_account_id=0,
        order_type="limit",
        post_only=True,
        reduce_only=False,
    )


def test_envelope_base64_roundtrip(monkeypatch):
    monkeypatch.setenv("SWIFT_ENVELOPE_FORMAT", "base64")
    kp = Keypair()
    params = make_params()
    creator = SwiftEnvelopeCreator()
    env = creator.create_order_envelope(params, kp)

    # Top-level fields
    assert "message" in env and isinstance(env["message"], str)
    assert "signature" in env and isinstance(env["signature"], str)
    assert env["market_index"] == 0
    assert env["market_type"] == "perp"
    assert env["taker_authority"] == params.taker_authority

    # Base64 decodes to JSON message with expected structure
    raw = base64.b64decode(env["message"]).decode("utf-8")
    msg = json.loads(raw)
    assert msg["type"] == "order"
    assert msg["data"]["market_index"] == 0
    assert msg["data"]["side"] == "buy"


def test_envelope_raw_format(monkeypatch):
    monkeypatch.setenv("SWIFT_ENVELOPE_FORMAT", "raw")
    kp = Keypair()
    params = make_params()
    creator = SwiftEnvelopeCreator()
    env = creator.create_order_envelope(params, kp)

    assert isinstance(env["message"], dict)
    msg = env["message"]
    assert msg["type"] == "order"
    assert msg["data"]["market_index"] == 0
    assert msg["data"]["side"] == "buy"


def test_validation_rejects_bad_params(monkeypatch):
    monkeypatch.setenv("SWIFT_ENVELOPE_FORMAT", "base64")
    kp = Keypair()
    bad = make_params()
    bad.market_index = -1
    creator = SwiftEnvelopeCreator()
    with pytest.raises(ValueError):
        creator.create_order_envelope(bad, kp)


def test_circuit_breaker_trips(monkeypatch):
    monkeypatch.setenv("SWIFT_ENVELOPE_FORMAT", "base64")
    monkeypatch.setenv("SWIFT_ENVELOPE_MAX_FAILS", "2")
    kp = Keypair()
    bad = make_params()
    bad.price = -1.0
    creator = SwiftEnvelopeCreator()
    # First two calls raise ValueError
    for _ in range(2):
        with pytest.raises(ValueError):
            creator.create_order_envelope(bad, kp)
    # Third call trips breaker
    with pytest.raises(CircuitBreakerOpen):
        creator.create_order_envelope(bad, kp)

