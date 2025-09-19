"""
Core modules for Ultimate Hedge Bot.

Contains the main business logic and safety layers.
"""

from .state_machine import HedgeStateMachine, HedgeState, TransitionError
from .safe_drift_client import SafeDriftClient
from .xemm_bridge import xemm_bridge, minimal_xemm_bridge, MinimalXEMMBridge
from .effective_cost_router import EffectiveCostRouter
from .urgency_scorer import UrgencyScorer
from .audit_trail import audit_trail, AuditTrail
from .safe_config_manager import SafeConfigManager
from .main import main

__all__ = [
    'HedgeStateMachine', 'HedgeState', 'TransitionError',
    'SafeDriftClient',
    'xemm_bridge', 'minimal_xemm_bridge', 'MinimalXEMMBridge',
    'EffectiveCostRouter', 'UrgencyScorer',
    'audit_trail', 'AuditTrail',
    'SafeConfigManager',
    'main'
]