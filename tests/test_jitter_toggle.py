import asyncio

from libs.jitter.runtime import resolve_jitter_settings
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
