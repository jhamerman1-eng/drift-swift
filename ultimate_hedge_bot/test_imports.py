#!/usr/bin/env python3
"""
Test script to isolate import issues
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    print("Testing core imports...")
    from core.state_machine import HedgeStateMachine, HedgeContext, HedgeState
    print("✅ Core imports successful")

    print("Testing coordination imports...")
    from coordination.attribution import StrategySource, AttributedFill, FillAttributor
    print("✅ Attribution imports successful")

    from coordination.strategy_coordinator import StrategyCoordinator, DeltaState
    print("✅ Strategy coordinator imports successful")

    print("Testing coordination realtime integration...")
    from coordination.realtime_integration import RealTimeIntegrationEngine
    print("✅ Real-time integration imports successful")

    print("All imports successful!")

except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()


