"""
Execution Router Module

Intent-based order routing for maker vs taker execution with proper
flag enforcement, precision normalization, and error handling.
"""

from .router import ExecutionRouter, ExecIntent, OrderResult, ExecutionMetrics

__all__ = ['ExecutionRouter', 'ExecIntent', 'OrderResult', 'ExecutionMetrics']
