#!/usr/bin/env python3
"""
Drift-Swift Bot Orchestrator Package

Provides comprehensive bot orchestration with:
- Lifecycle management (start/stop/restart bots)
- Health monitoring and HTTP endpoints
- Consolidated metrics collection
- Market regime classification
- Graceful shutdown handling
"""

from .master import Orchestrator, BotState

__all__ = [
    'Orchestrator',
    'BotState'
]

__version__ = "1.0.0"