#!/usr/bin/env python3
"""
Centralized environment loader for orchestrated bots.

Reads a single YAML config (e.g. configs/core/drift_client.yaml) and
produces a dict of environment variables to pass to all bot subprocesses.

This avoids each bot doing its own wallet/RPC discovery.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import os
import yaml


def build_shared_env(config_path: str = "configs/core/drift_client.yaml") -> Dict[str, str]:
    p = Path(config_path)
    if not p.exists():
        # Return current environment selection but don't fail hard
        return {
            "DRIFT_ENV": os.getenv("DRIFT_ENV", "devnet"),
            "USE_MOCK": os.getenv("USE_MOCK", "false"),
        }

    with open(p, "r") as f:
        cfg: Dict[str, Any] = yaml.safe_load(f) or {}

    # Support multiple schema shapes
    rpc_http = None
    rpc_ws = None
    if isinstance(cfg.get("rpc"), dict):
        rpc_http = cfg["rpc"].get("http_url")
        rpc_ws = cfg["rpc"].get("ws_url")
    rpc_http = cfg.get("rpc_url", rpc_http)

    wallets = cfg.get("wallets") or {}
    keypair_path = wallets.get("maker_keypair_path") or cfg.get("wallet")
    swift_cfg = cfg.get("swift") or {}
    swift_http = swift_cfg.get("http_url")
    swift_ws = swift_cfg.get("ws_url")

    shared = {
        "DRIFT_ENV": str(cfg.get("cluster", cfg.get("env", "devnet"))).lower(),
        "DRIFT_RPC_URL": str(rpc_http or ""),
        "DRIFT_WS_URL": str(rpc_ws or ""),
        "DRIFT_KEYPAIR_PATH": str(keypair_path or ""),
        "USE_MOCK": "true" if cfg.get("use_mock") else os.getenv("USE_MOCK", "false"),
        "SWIFT_SIDECAR_URL": str(swift_http or ""),
        "SWIFT_WEBSOCKET_URL": str(swift_ws or ""),
    }

    # Do not inject empty values (keep existing env if present)
    out: Dict[str, str] = {}
    for k, v in shared.items():
        if v:
            out[k] = v

    # Provide common synonyms expected by some scripts
    if out.get("DRIFT_RPC_URL") and not out.get("RPC_URL"):
        out["RPC_URL"] = out["DRIFT_RPC_URL"]
    if out.get("DRIFT_WS_URL") and not out.get("WS_URL"):
        out["WS_URL"] = out["DRIFT_WS_URL"]
    return out


if __name__ == "__main__":
    env = build_shared_env()
    for k, v in env.items():
        print(f"{k}={v}")
