"""
Bot Profile Management

Bot-specific configuration profiles with inheritance and validation guardrails.
"""

from .base import BaseProfile, ProfileValidationError
from .jit import JITProfile
from .hedge import HedgeProfile  
from .trend import TrendProfile
from .manager import ProfileManager, get_bot_profile

__all__ = [
    "BaseProfile",
    "ProfileValidationError",
    "JITProfile",
    "HedgeProfile", 
    "TrendProfile",
    "ProfileManager",
    "get_bot_profile"
]
