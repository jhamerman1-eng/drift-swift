"""
Core Settings Module

Immutable, validated, and cached configuration management for Drift trading bots.
Provides contract versioning, environment overlays, and production-grade guardrails.
"""

from .settings import CoreSettings
from .cache import get_core, reload_if_changed, get_generation
from .loader import load_core
from .health import run_health_checks, HealthCheck
from .validator import validate_startup
from .diff import compute_config_diff
from .observability import write_snapshot, get_provenance

__all__ = [
    "CoreSettings",
    "get_core", 
    "reload_if_changed",
    "get_generation",
    "load_core",
    "run_health_checks",
    "HealthCheck", 
    "validate_startup",
    "compute_config_diff",
    "write_snapshot",
    "get_provenance"
]
