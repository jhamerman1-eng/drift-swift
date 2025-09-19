import pytest

from libs.jitter.runtime import JitterSettings, resolve_jitter_settings


def test_resolve_jitter_settings_defaults():
    settings = resolve_jitter_settings({})
    assert isinstance(settings, JitterSettings)
    assert settings.enabled is False
    assert settings.backend == "ts-sidecar"
    assert settings.mode == "shotgun"
    assert settings.auction_ignore_swift is True


def test_resolve_jitter_settings_env_override():
    env = {
        "JITTER_ENABLED": "1",
        "JITTER_BACKEND": "py-legacy",
        "JITTER_MODE": "sniper",
        "AUCTION_IGNORE_SWIFT": "0",
    }
    settings = resolve_jitter_settings({}, env=env)
    assert settings.enabled is True
    assert settings.backend == "py-legacy"
    assert settings.mode == "sniper"
    assert settings.auction_ignore_swift is False
    assert settings.uses_python_backend()
    assert settings.source == "env"


@pytest.mark.parametrize(
    "backend,expected_python",
    [("py-legacy", True), ("ts-sidecar", False)],
)
def test_uses_python_backend_flag(backend, expected_python):
    settings = resolve_jitter_settings({
        "jitter_enabled": True,
        "jitter_backend": backend,
        "jitter_mode": "shotgun",
        "auction_ignore_swift": True,
    })
    assert settings.uses_python_backend() is expected_python
    assert settings.uses_sidecar_backend() is (settings.enabled and backend == "ts-sidecar")
