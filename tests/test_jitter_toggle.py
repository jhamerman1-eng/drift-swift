import asyncio

import sys
import types

from libs.jitter.runtime import resolve_jitter_settings


def _install_runtime_stubs() -> None:
    if "driftpy" not in sys.modules:
        driftpy_module = types.ModuleType("driftpy")
        sys.modules["driftpy"] = driftpy_module

        drift_client_module = types.ModuleType("driftpy.drift_client")
        setattr(drift_client_module, "DriftClient", object)
        sys.modules["driftpy.drift_client"] = drift_client_module

        types_module = types.ModuleType("driftpy.types")
        for name in ["OrderParams", "OrderType", "PositionDirection", "PostOnlyParams"]:
            setattr(types_module, name, type(name, (), {}))
        sys.modules["driftpy.types"] = types_module

    if "solders" not in sys.modules:
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


_install_runtime_stubs()

from run_swift_mm_complete import CompleteSwiftMMBot


class DummyBot(CompleteSwiftMMBot):
    """Helper subclass that avoids heavy __init__ logic by stubbing dependencies."""

    def __init__(self):
        # Bypass parent __init__ entirely
        pass


def test_apply_runtime_config_switches_to_python(monkeypatch):
    bot = DummyBot()
    bot.config = {}
    bot.jit_enabled = False
    bot.jitter_settings = resolve_jitter_settings({"jitter_enabled": False})
    bot.jit_client = None
    bot._apply_jitter_settings = CompleteSwiftMMBot._apply_jitter_settings.__get__(bot, CompleteSwiftMMBot)

    init_called = False

    async def fake_init():
        nonlocal init_called
        init_called = True

    bot._initialize_jit_client = fake_init  # type: ignore

    asyncio.run(bot.apply_runtime_config({
        "jitter": {
            "jitter_enabled": True,
            "jitter_backend": "py-legacy",
            "jitter_mode": "sniper",
            "auction_ignore_swift": True,
        }
    }))

    assert bot.jitter_settings.uses_python_backend()
    assert init_called is True
    assert bot.jit_enabled is True


def test_apply_runtime_config_disables_python_backend(monkeypatch):
    bot = DummyBot()
    bot.config = {}
    bot.jit_enabled = False
    bot.jitter_settings = resolve_jitter_settings({
        "jitter_enabled": True,
        "jitter_backend": "py-legacy",
        "jitter_mode": "shotgun",
        "auction_ignore_swift": True,
    })
    bot.jit_client = object()
    bot._apply_jitter_settings = CompleteSwiftMMBot._apply_jitter_settings.__get__(bot, CompleteSwiftMMBot)

    async def fake_init():
        raise AssertionError("_initialize_jit_client should not be called when switching away from python backend")

    bot._initialize_jit_client = fake_init  # type: ignore

    asyncio.run(bot.apply_runtime_config({
        "jitter": {
            "jitter_enabled": True,
            "jitter_backend": "ts-sidecar",
            "jitter_mode": "shotgun",
            "auction_ignore_swift": True,
        }
    }))

    assert bot.jitter_settings.uses_sidecar_backend()
    assert bot.jit_client is None
    assert bot.jit_enabled is False
