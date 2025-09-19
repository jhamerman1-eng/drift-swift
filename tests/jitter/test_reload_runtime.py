import asyncio
import sys
import types
from pathlib import Path

import pytest
import yaml

from libs.jitter.runtime import resolve_jitter_settings


def _install_driftpy_stubs() -> None:
    if "driftpy" in sys.modules:
        return

    driftpy_module = types.ModuleType("driftpy")
    sys.modules["driftpy"] = driftpy_module

    drift_client_module = types.ModuleType("driftpy.drift_client")
    setattr(drift_client_module, "DriftClient", object)
    sys.modules["driftpy.drift_client"] = drift_client_module

    types_module = types.ModuleType("driftpy.types")
    for name in ["OrderParams", "OrderType", "PositionDirection", "PostOnlyParams"]:
        setattr(types_module, name, type(name, (), {}))
    sys.modules["driftpy.types"] = types_module

    solders_module = types.ModuleType("solders")
    keypair_module = types.ModuleType("solders.keypair")

    class _KeypairStub:
        def __init__(self, *_, **__):
            pass

        @staticmethod
        def from_bytes(data):  # type: ignore[override]
            return _KeypairStub()

        def pubkey(self):  # type: ignore[override]
            return "StubPubkey"

    keypair_module.Keypair = _KeypairStub
    solders_module.keypair = keypair_module
    sys.modules["solders"] = solders_module
    sys.modules["solders.keypair"] = keypair_module


_install_driftpy_stubs()

from run_swift_mm_complete import CompleteSwiftMMBot


class ReloadDummyBot(CompleteSwiftMMBot):
    def __init__(self):  # pragma: no cover - intentionally bypass heavy init
        pass


def test_reload_runtime_config_enables_python_backend(tmp_path: Path):
    config_path = tmp_path / "jit.yaml"
    with config_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            {
                "jitter": {
                    "jitter_enabled": True,
                    "jitter_backend": "py-legacy",
                    "jitter_mode": "sniper",
                    "auction_ignore_swift": False,
                }
            },
            fh,
        )

    bot = ReloadDummyBot()
    bot.config = {}
    bot.runtime_config_path = config_path
    bot.jitter_settings = resolve_jitter_settings({})
    bot.jitter_backend = bot.jitter_settings.backend
    bot.jitter_mode = bot.jitter_settings.mode
    bot.auction_ignore_swift = bot.jitter_settings.auction_ignore_swift
    bot.ts_jitter_enabled = False
    bot.jitter_params_snapshot_ts = 0.0
    bot._runtime_reload_lock = None
    bot._runtime_config_cache = {}
    bot.jit_client = None
    bot.jit_enabled = False

    init_called = False

    async def fake_init():
        nonlocal init_called
        init_called = True

    bot._initialize_jit_client = fake_init  # type: ignore

    asyncio.run(bot.reload_runtime_config(reason="test"))

    assert init_called is True
    assert bot.jitter_settings.uses_python_backend()
    assert bot.jit_enabled is True
    assert bot.config["jitter"]["jitter_mode"] == "sniper"


def test_reload_runtime_config_switches_to_sidecar(tmp_path: Path):
    config_path = tmp_path / "jit.yaml"
    with config_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            {
                "jitter": {
                    "jitter_enabled": True,
                    "jitter_backend": "ts-sidecar",
                    "jitter_mode": "shotgun",
                    "auction_ignore_swift": True,
                }
            },
            fh,
        )

    bot = ReloadDummyBot()
    bot.config = {}
    bot.runtime_config_path = config_path
    bot.jitter_settings = resolve_jitter_settings({
        "jitter_enabled": True,
        "jitter_backend": "py-legacy",
        "jitter_mode": "shotgun",
        "auction_ignore_swift": True,
    })
    bot.jitter_backend = bot.jitter_settings.backend
    bot.jitter_mode = bot.jitter_settings.mode
    bot.auction_ignore_swift = bot.jitter_settings.auction_ignore_swift
    bot.ts_jitter_enabled = False
    bot.jitter_params_snapshot_ts = 0.0
    bot._runtime_reload_lock = None
    bot._runtime_config_cache = {}
    bot.jit_client = object()
    bot.jit_enabled = True

    async def fake_health():
        return False

    bot._check_swift_sidecar_health = fake_health  # type: ignore

    asyncio.run(bot.reload_runtime_config(reason="test"))

    assert bot.jitter_settings.uses_sidecar_backend()
    assert bot.jit_client is None
    assert bot.jit_enabled is False
    # Health failure should disable ts_jitter_enabled locally
    assert bot.ts_jitter_enabled is False
