#!/usr/bin/env python3
"""
Simple test to check if the dashboard components work
"""

import sys
import os

# Add paths
sys.path.append('drift-bots')
sys.path.append('drift-bots/libs')

print("Testing dashboard imports...")

try:
    from libs.drift.client import EnhancedMockDriftClient
    print("✅ EnhancedMockDriftClient imported successfully")
except Exception as e:
    print(f"❌ EnhancedMockDriftClient import failed: {e}")

try:
    # This import might fail due to module path issues
    import importlib.util
    spec = importlib.util.spec_from_file_location("dashboard", "drift-bots/comprehensive_pnl_dashboard.py")
    dashboard_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dashboard_module)
    ComprehensivePnLDashboard = dashboard_module.ComprehensivePnLDashboard
    print("✅ ComprehensivePnLDashboard imported successfully")
except Exception as e:
    print(f"❌ ComprehensivePnLDashboard import failed: {e}")

print("Basic import test complete")
