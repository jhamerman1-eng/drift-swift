"""
Real-time Strategy Optimization - Feature Flagged

Auto-tuning of strategy parameters based on performance feedback.
Only available when realtime_optimization feature flag is enabled.

Features:
- Bayesian optimization of parameters
- Online learning for regime adaptation
- Performance-driven parameter tuning
- A/B testing for parameter changes
"""

import asyncio
import logging
import time
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..feature_flags import has_realtime_optimization, has_advanced_quality_filters

logger = logging.getLogger("jitter.advanced.optimization")

class OptimizationObjective(Enum):
    """Optimization objectives"""
    MAXIMIZE_PNL = "maximize_pnl"
    MAXIMIZE_SHARPE = "maximize_sharpe"
    MAXIMIZE_FILL_RATE = "maximize_fill_rate"
    MINIMIZE_LATENCY = "minimize_latency"
    MAXIMIZE_WIN_RATE = "maximize_win_rate"

class ParameterType(Enum):
    """Types of parameters that can be optimized"""
    CONTINUOUS = "continuous"      # Float values with bounds
    DISCRETE = "discrete"          # Integer values with bounds
    CATEGORICAL = "categorical"    # String values from set

@dataclass
class ParameterDefinition:
    """Definition of an optimizable parameter"""
    name: str
    param_type: ParameterType
    bounds: Tuple[float, float] = (0.0, 1.0)  # For continuous/discrete
    categories: List[str] = field(default_factory=list)  # For categorical
    current_value: Any = None
    importance_weight: float = 1.0

@dataclass
class PerformanceSnapshot:
    """Performance snapshot for optimization"""
    timestamp: float
    parameters: Dict[str, Any]
    objective_value: float
    fill_count: int
    win_rate: float
    avg_latency_ms: float
    sharpe_ratio: float
    total_pnl: float
    regime: str = "normal"

class RealtimeOptimizer:
    """
    Real-time parameter optimization using Bayesian optimization and online learning.
    
    Only functional when feature flag is enabled, otherwise provides static parameters.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = has_realtime_optimization()
        
        if not self.enabled:
            logger.info("📊 Real-time Optimization DISABLED (feature flag off)")
            return
        
        # Require quality filters for optimization
        if not has_advanced_quality_filters():
            logger.warning("📊 Real-time Optimization requires advanced quality filters. Disabling.")
            self.enabled = False
            return
        
        # Define optimizable parameters
        self.parameters = self._initialize_parameters()
        
        # Optimization state
        self.objective = OptimizationObjective(config.get("objective", "maximize_pnl"))
        self.performance_history: List[PerformanceSnapshot] = []
        self.current_experiment: Optional[Dict[str, Any]] = None
        
        # Optimization settings
        self.min_samples_for_optimization = config.get("min_samples", 50)
        self.optimization_interval_seconds = config.get("optimization_interval", 3600)  # 1 hour
        self.exploration_rate = config.get("exploration_rate", 0.1)  # 10% exploration
        self.convergence_threshold = config.get("convergence_threshold", 0.01)  # 1% improvement
        
        # Safety limits
        self.max_parameter_change_per_step = config.get("max_change_per_step", 0.1)  # 10% max change
        self.performance_degradation_threshold = config.get("degradation_threshold", 0.15)  # 15% worse = revert
        self.rollback_enabled = config.get("enable_rollback", True)
        
        # State tracking
        self.last_optimization_time = 0.0
        self.optimization_count = 0
        self.best_performance = None
        self.baseline_performance = None
        
        # Callbacks
        self.parameter_update_callback: Optional[Callable] = None
        
        logger.info("📊 Real-time Optimization ENABLED")
        logger.info(f"   Objective: {self.objective.value}")
        logger.info(f"   Optimization interval: {self.optimization_interval_seconds}s")
        logger.info(f"   Exploration rate: {self.exploration_rate:.1%}")
    
    def _initialize_parameters(self) -> Dict[str, ParameterDefinition]:
        """Initialize optimizable parameters"""
        
        params = {
            # Shotgun parameters
            "shotgun_clip_size": ParameterDefinition(
                name="shotgun_clip_size",
                param_type=ParameterType.CONTINUOUS,
                bounds=(0.1, 1.0),
                current_value=0.25,
                importance_weight=1.0
            ),
            "shotgun_toxicity_max": ParameterDefinition(
                name="shotgun_toxicity_max",
                param_type=ParameterType.CONTINUOUS,
                bounds=(0.5, 0.99),
                current_value=0.95,
                importance_weight=0.8
            ),
            
            # Sniper parameters
            "sniper_clip_size": ParameterDefinition(
                name="sniper_clip_size",
                param_type=ParameterType.CONTINUOUS,
                bounds=(1.0, 10.0),
                current_value=2.0,
                importance_weight=1.0
            ),
            "sniper_toxicity_max": ParameterDefinition(
                name="sniper_toxicity_max",
                param_type=ParameterType.CONTINUOUS,
                bounds=(0.2, 0.8),
                current_value=0.35,
                importance_weight=0.9
            ),
            "sniper_min_notional": ParameterDefinition(
                name="sniper_min_notional",
                param_type=ParameterType.CONTINUOUS,
                bounds=(500.0, 5000.0),
                current_value=2000.0,
                importance_weight=0.7
            ),
            
            # Quality filter parameters
            "quality_composite_min": ParameterDefinition(
                name="quality_composite_min",
                param_type=ParameterType.CONTINUOUS,
                bounds=(0.3, 0.8),
                current_value=0.5,
                importance_weight=0.8
            ),
            
            # Allocation parameters
            "allocation_response_speed": ParameterDefinition(
                name="allocation_response_speed",
                param_type=ParameterType.CONTINUOUS,
                bounds=(0.1, 2.0),
                current_value=1.0,
                importance_weight=0.6
            )
        }
        
        return params
    
    def is_available(self) -> bool:
        """Check if real-time optimization is available"""
        return self.enabled
    
    async def record_performance(self, performance_data: Dict[str, Any]):
        """Record performance data for optimization"""
        
        if not self.enabled:
            return
        
        try:
            # Extract current parameter values
            current_params = {name: param.current_value for name, param in self.parameters.items()}
            
            # Create performance snapshot
            snapshot = PerformanceSnapshot(
                timestamp=time.time(),
                parameters=current_params.copy(),
                objective_value=self._calculate_objective_value(performance_data),
                fill_count=performance_data.get("fill_count", 0),
                win_rate=performance_data.get("win_rate", 0.5),
                avg_latency_ms=performance_data.get("avg_latency_ms", 100.0),
                sharpe_ratio=performance_data.get("sharpe_ratio", 0.0),
                total_pnl=performance_data.get("total_pnl", 0.0),
                regime=performance_data.get("regime", "normal")
            )
            
            self.performance_history.append(snapshot)
            
            # Limit memory usage
            if len(self.performance_history) > 10000:
                self.performance_history = self.performance_history[-5000:]
            
            # Check if optimization should run
            await self._check_optimization_trigger()
            
        except Exception as e:
            logger.error(f"❌ Performance recording failed: {e}")
    
    def _calculate_objective_value(self, performance_data: Dict[str, Any]) -> float:
        """Calculate objective value based on optimization goal"""
        
        if self.objective == OptimizationObjective.MAXIMIZE_PNL:
            return performance_data.get("total_pnl", 0.0)
        elif self.objective == OptimizationObjective.MAXIMIZE_SHARPE:
            return performance_data.get("sharpe_ratio", 0.0)
        elif self.objective == OptimizationObjective.MAXIMIZE_FILL_RATE:
            return performance_data.get("fill_rate", 0.0)
        elif self.objective == OptimizationObjective.MINIMIZE_LATENCY:
            return -performance_data.get("avg_latency_ms", 100.0)  # Negative for minimization
        elif self.objective == OptimizationObjective.MAXIMIZE_WIN_RATE:
            return performance_data.get("win_rate", 0.5)
        else:
            return 0.0
    
    async def _check_optimization_trigger(self):
        """Check if optimization should be triggered"""
        
        current_time = time.time()
        
        # Check time-based trigger
        if current_time - self.last_optimization_time < self.optimization_interval_seconds:
            return
        
        # Check minimum samples
        if len(self.performance_history) < self.min_samples_for_optimization:
            return
        
        # Trigger optimization
        await self._run_optimization()
    
    async def _run_optimization(self):
        """Run Bayesian optimization to find better parameters"""
        
        try:
            logger.info("📊 Starting parameter optimization...")
            
            # Analyze recent performance
            recent_window = 3600  # Last hour
            recent_performance = [
                p for p in self.performance_history 
                if time.time() - p.timestamp < recent_window
            ]
            
            if len(recent_performance) < 10:
                logger.warning("📊 Insufficient recent data for optimization")
                return
            
            # Calculate baseline performance
            if self.baseline_performance is None:
                self.baseline_performance = np.mean([p.objective_value for p in recent_performance[:10]])
            
            # Find best performing parameter combinations
            best_params = await self._bayesian_optimization(recent_performance)
            
            # Apply parameter updates with safety checks
            await self._apply_parameter_updates(best_params)
            
            self.last_optimization_time = time.time()
            self.optimization_count += 1
            
            logger.info(f"📊 Optimization completed (run #{self.optimization_count})")
            
        except Exception as e:
            logger.error(f"❌ Optimization failed: {e}")
    
    async def _bayesian_optimization(self, performance_data: List[PerformanceSnapshot]) -> Dict[str, Any]:
        """Simplified Bayesian optimization (in practice, use proper BO library)"""
        
        # Extract parameter vectors and objective values
        param_vectors = []
        objective_values = []
        
        for snapshot in performance_data:
            vector = []
            for param_name in sorted(self.parameters.keys()):
                value = snapshot.parameters.get(param_name, self.parameters[param_name].current_value)
                vector.append(value)
            param_vectors.append(vector)
            objective_values.append(snapshot.objective_value)
        
        if not param_vectors:
            return {}
        
        # Find best performing parameters (simplified approach)
        best_idx = np.argmax(objective_values)
        best_vector = param_vectors[best_idx]
        best_objective = objective_values[best_idx]
        
        # Create suggestion based on best + exploration
        suggested_params = {}
        param_names = sorted(self.parameters.keys())
        
        for i, param_name in enumerate(param_names):
            param_def = self.parameters[param_name]
            best_value = best_vector[i]
            
            # Add exploration noise
            if np.random.random() < self.exploration_rate:
                # Explore around best value
                if param_def.param_type == ParameterType.CONTINUOUS:
                    noise_scale = (param_def.bounds[1] - param_def.bounds[0]) * 0.1
                    suggested_value = best_value + np.random.normal(0, noise_scale)
                    suggested_value = np.clip(suggested_value, param_def.bounds[0], param_def.bounds[1])
                else:
                    suggested_value = best_value
            else:
                suggested_value = best_value
            
            suggested_params[param_name] = suggested_value
        
        logger.info(f"📊 Best objective: {best_objective:.4f}, suggesting parameters: {suggested_params}")
        return suggested_params
    
    async def _apply_parameter_updates(self, suggested_params: Dict[str, Any]):
        """Apply parameter updates with safety checks"""
        
        updates_applied = {}
        
        for param_name, suggested_value in suggested_params.items():
            if param_name not in self.parameters:
                continue
            
            param_def = self.parameters[param_name]
            current_value = param_def.current_value
            
            # Apply maximum change limit
            if param_def.param_type == ParameterType.CONTINUOUS:
                max_change = abs(current_value * self.max_parameter_change_per_step)
                if abs(suggested_value - current_value) > max_change:
                    # Limit the change
                    if suggested_value > current_value:
                        suggested_value = current_value + max_change
                    else:
                        suggested_value = current_value - max_change
            
            # Validate bounds
            if param_def.param_type in [ParameterType.CONTINUOUS, ParameterType.DISCRETE]:
                suggested_value = np.clip(suggested_value, param_def.bounds[0], param_def.bounds[1])
            
            # Apply update
            if suggested_value != current_value:
                param_def.current_value = suggested_value
                updates_applied[param_name] = {
                    "old_value": current_value,
                    "new_value": suggested_value,
                    "change_pct": abs(suggested_value - current_value) / abs(current_value) if current_value != 0 else 0.0
                }
        
        # Notify system of parameter changes
        if updates_applied and self.parameter_update_callback:
            await self.parameter_update_callback(updates_applied)
        
        if updates_applied:
            logger.info(f"📊 Applied parameter updates: {updates_applied}")
        else:
            logger.info("📊 No parameter updates needed")
    
    async def rollback_to_baseline(self, reason: str = "performance_degradation"):
        """Rollback parameters to known good baseline"""
        
        if not self.enabled or not self.rollback_enabled:
            return
        
        if self.best_performance is None:
            logger.warning("📊 No baseline performance to rollback to")
            return
        
        try:
            # Find best performing parameter set
            best_snapshot = max(self.performance_history, key=lambda p: p.objective_value)
            
            rollback_updates = {}
            for param_name, param_def in self.parameters.items():
                if param_name in best_snapshot.parameters:
                    old_value = param_def.current_value
                    new_value = best_snapshot.parameters[param_name]
                    param_def.current_value = new_value
                    rollback_updates[param_name] = {
                        "old_value": old_value,
                        "new_value": new_value
                    }
            
            # Notify system
            if rollback_updates and self.parameter_update_callback:
                await self.parameter_update_callback(rollback_updates)
            
            logger.warning(f"📊 Rolled back parameters due to: {reason}")
            logger.info(f"📊 Rollback updates: {rollback_updates}")
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
    
    def set_parameter_update_callback(self, callback: Callable):
        """Set callback for parameter updates"""
        self.parameter_update_callback = callback
        logger.info("📊 Parameter update callback configured")
    
    def get_current_parameters(self) -> Dict[str, Any]:
        """Get current parameter values"""
        if not self.enabled:
            return {}
        
        return {name: param.current_value for name, param in self.parameters.items()}
    
    def manually_set_parameter(self, param_name: str, value: Any) -> bool:
        """Manually override a parameter value"""
        if not self.enabled or param_name not in self.parameters:
            return False
        
        param_def = self.parameters[param_name]
        
        # Validate value
        if param_def.param_type in [ParameterType.CONTINUOUS, ParameterType.DISCRETE]:
            value = np.clip(value, param_def.bounds[0], param_def.bounds[1])
        
        old_value = param_def.current_value
        param_def.current_value = value
        
        logger.info(f"📊 Manual parameter update: {param_name} {old_value} -> {value}")
        return True
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        if not self.enabled:
            return {"feature_enabled": False}
        
        if not self.performance_history:
            return {"feature_enabled": True, "data_available": False}
        
        recent_performance = [
            p for p in self.performance_history 
            if time.time() - p.timestamp < 3600
        ]
        
        current_params = self.get_current_parameters()
        
        # Calculate performance trend
        if len(recent_performance) >= 2:
            recent_values = [p.objective_value for p in recent_performance]
            trend = (recent_values[-1] - recent_values[0]) / max(abs(recent_values[0]), 1e-6)
        else:
            trend = 0.0
        
        # Best performance
        if self.performance_history:
            best_performance = max(p.objective_value for p in self.performance_history)
            current_performance = recent_performance[-1].objective_value if recent_performance else 0.0
        else:
            best_performance = 0.0
            current_performance = 0.0
        
        return {
            "feature_enabled": True,
            "data_available": True,
            "optimization_count": self.optimization_count,
            "last_optimization": self.last_optimization_time,
            "objective": self.objective.value,
            "current_parameters": current_params,
            "performance_trend_1h": trend,
            "best_performance": best_performance,
            "current_performance": current_performance,
            "samples_collected": len(self.performance_history),
            "exploration_rate": self.exploration_rate
        }




