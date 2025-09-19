"""
Ultimate Hedge Bot - Coordination Package
Real-time MM bot integration with comprehensive attribution and strategy coordination.
"""

from .attribution import (
    StrategySource,
    FillOutcome,
    AttributedFill,
    FillAttributor,
    create_fill_attributor
)

from .strategy_coordinator import (
    DeltaState,
    StrategyConfig,
    StrategyCoordinator,
    create_strategy_coordinator
)

from .realtime_integration import (
    HedgeRequest,
    HedgeResult,
    RealTimeIntegrationEngine,
    create_realtime_integration_engine
)

__all__ = [
    # Attribution
    'StrategySource',
    'FillOutcome', 
    'AttributedFill',
    'FillAttributor',
    'create_fill_attributor',
    
    # Strategy Coordination
    'DeltaState',
    'StrategyConfig', 
    'StrategyCoordinator',
    'create_strategy_coordinator',
    
    # Real-time Integration
    'HedgeRequest',
    'HedgeResult',
    'RealTimeIntegrationEngine',
    'create_realtime_integration_engine'
]

__version__ = "1.0.0"

