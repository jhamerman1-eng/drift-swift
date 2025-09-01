#!/usr/bin/env python3
"""
Smoke-test for Swift Sidecar
"""
import json
from libs.drift.swift_sidecar_driver import SwiftSidecarDriver

def main():
    driver = SwiftSidecarDriver(base_url="http://localhost:8787")
    # This is a fake envelope for smoke test; replace with a real signed envelope in live runs.
    envelope = {
        "message": "BASE64_OR_HEX_SIGNED_MSG",
        "signature": "BASE64_OR_HEX_SIGNATURE",
        "market_index": 0,
        "market_type": "perp",
        "taker_authority": "YourPubkeyHere"
    }
    ack = driver.place_order(envelope)
    print("ACK:", json.dumps(ack, indent=2))
    if "id" in ack:
        res = driver.cancel_order(ack["id"])
        print("CANCEL:", json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
