"""Runtime helpers for Jitter configuration toggles."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Mapping

_VALID_BACKENDS = {"ts-sidecar", "py-legacy"}
_VALID_MODES = {"shotgun", "sniper"}


def _env_bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    value = env.get(key.upper())
    if value is None:
        return default
    value = value.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _env_choice(env: Mapping[str, str], key: str, default: str, *, valid: set[str]) -> str:
    value = env.get(key.upper())
    if value is None:
        return default
    value = value.strip().lower()
    return value if value in valid else default


@dataclass(frozen=True)
class JitterSettings:
    """Resolved runtime configuration for Jitter integration."""

    enabled: bool
    backend: str
    mode: str
    auction_ignore_swift: bool
    source: str = "config"
    raw: Dict[str, object] = field(default_factory=dict)

    def uses_python_backend(self) -> bool:
        return self.enabled and self.backend == "py-legacy"

    def uses_sidecar_backend(self) -> bool:
        return self.enabled and self.backend == "ts-sidecar"


def resolve_jitter_settings(config: Mapping[str, object] | None, *, env: Mapping[str, str] | None = None) -> JitterSettings:
    """Resolve jitter configuration with environment overrides.

    Args:
        config: Mapping from config file (e.g. configs/bots/jit.yaml::jitter)
        env: Optional mapping to use instead of os.environ (useful for tests)

    Returns:
        JitterSettings with normalized values.
    """

    config = dict(config or {})
    env = env or os.environ

    enabled_default = bool(config.get("jitter_enabled", False))
    backend_default = str(config.get("jitter_backend", "ts-sidecar")).strip().lower()
    if backend_default not in _VALID_BACKENDS:
        backend_default = "py-legacy"
    mode_default = str(config.get("jitter_mode", "shotgun")).strip().lower()
    if mode_default not in _VALID_MODES:
        mode_default = "shotgun"
    ignore_swift_default = bool(config.get("auction_ignore_swift", True))

    enabled = _env_bool(env, "JITTER_ENABLED", enabled_default)
    backend = _env_choice(env, "JITTER_BACKEND", backend_default, valid=_VALID_BACKENDS)
    mode = _env_choice(env, "JITTER_MODE", mode_default, valid=_VALID_MODES)
    auction_ignore_swift = _env_bool(env, "AUCTION_IGNORE_SWIFT", ignore_swift_default)

    source = "env" if any(
        key in env and env[key] != "" for key in ["JITTER_ENABLED", "JITTER_BACKEND", "JITTER_MODE", "AUCTION_IGNORE_SWIFT"]
    ) else "config"

    return JitterSettings(
        enabled=enabled,
        backend=backend,
        mode=mode,
        auction_ignore_swift=auction_ignore_swift,
        source=source,
        raw=config,
    )


__all__ = ["JitterSettings", "resolve_jitter_settings"]

