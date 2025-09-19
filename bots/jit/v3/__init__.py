"""
JIT v3.0 Engine Package

Production-ready JIT engine with:
- Regime-aware microprice calculation
- Spoof filter with depth analysis  
- Toxicity-based spread adjustment
- Enhanced cancel/replace logic
- Rails integration
- Comprehensive error handling
"""

# Core engine classes
from .core import (
    JITEngineV3,
    TradingClient
)

# Shared types
from .types import (
    MarketData,
    QuoteDecision,
    VolatilityRegime
)

# Component classes
from .components import (
    RegimeDetector,
    MicropriceCalculator,
    SpoofFilter,
    ToxicityCalculator,
    SpreadManagerV3,
    CancelReplaceV2,
    PerformanceTracker,
    JITMetricsV3
)

# Integration adapters
from .integration import (
    SwiftTradingClient,
    DriftPyTradingClient,
    JITEngineAdapter
)

# Components are now initialized directly in JITEngineV3.__init__

__version__ = "3.0.0"
__all__ = [
    "JITEngineV3",
    "MarketData", 
    "QuoteDecision",
    "VolatilityRegime",
    "TradingClient",
    "RegimeDetector",
    "MicropriceCalculator", 
    "SpoofFilter",
    "ToxicityCalculator",
    "SpreadManagerV3",
    "CancelReplaceV2",
    "PerformanceTracker",
    "JITMetricsV3",
    "SwiftTradingClient",
    "DriftPyTradingClient",
    "JITEngineAdapter"
]
