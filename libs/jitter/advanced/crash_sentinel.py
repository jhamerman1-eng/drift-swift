"""
Advanced Crash Sentinel Integration - Feature Flagged

Provides graduated risk response vs simple on/off switching.
Only available when advanced_crash_sentinel feature flag is enabled.

Features:
- Multi-level severity detection
- Graduated strategy scaling
- Cross-market risk monitoring
- Auto-recovery mechanisms
"""

import asyncio
import logging
import time
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from ..feature_flags import has_advanced_crash_sentinel
from ..types import StrategySource

logger = logging.getLogger("jitter.advanced.crash_sentinel")

class CrashSeverity(Enum):
    """Crash severity levels with different responses"""
    NORMAL = "normal"           # 0-1 sigma: Normal operations
    MINOR = "minor"             # 1-2 sigma: Mild caution
    MODERATE = "moderate"       # 2-3 sigma: Reduce exposure
    SEVERE = "severe"           # 3-4 sigma: Minimal operations
    EXTREME = "extreme"         # 4+ sigma: Emergency halt
    SYSTEMIC = "systemic"       # Multi-asset crash

class ResponseAction(Enum):
    """Response actions for different severity levels"""
    CONTINUE = "continue"
    SCALE_DOWN = "scale_down"
    SELECTIVE_HALT = "selective_halt"
    EMERGENCY_HALT = "emergency_halt"
    LIQUIDATE = "liquidate"

@dataclass
class MarketCondition:
    """Market condition snapshot for risk analysis"""
    price_change_1m: float = 0.0
    price_change_5m: float = 0.0
    volume_spike: float = 1.0        # Volume vs average
    volatility_spike: float = 1.0    # Volatility vs average
    oracle_deviation: float = 0.0    # Oracle vs market price
    timestamp: float = 0.0

@dataclass
class CrashResponse:
    """Response configuration for different severity levels"""
    severity: CrashSeverity
    shotgun_scale: float     # 0.0 = disabled, 1.0 = full
    sniper_scale: float      # 0.0 = disabled, 1.0 = full
    max_clip_scale: float    # Scale down clip sizes
    toxicity_tighten: float  # Tighten toxicity filters
    action: ResponseAction

class AdvancedCrashSentinel:
    """
    Advanced crash detection with graduated responses.
    
    Only functional when feature flag is enabled, otherwise acts as pass-through.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = has_advanced_crash_sentinel()
        
        if not self.enabled:
            logger.info("🚨 Advanced Crash Sentinel DISABLED (feature flag off)")
            return
        
        # Configure response matrix
        self.response_matrix = {
            CrashSeverity.NORMAL: CrashResponse(
                severity=CrashSeverity.NORMAL,
                shotgun_scale=1.0, sniper_scale=1.0,
                max_clip_scale=1.0, toxicity_tighten=1.0,
                action=ResponseAction.CONTINUE
            ),
            CrashSeverity.MINOR: CrashResponse(
                severity=CrashSeverity.MINOR,
                shotgun_scale=0.8, sniper_scale=0.9,
                max_clip_scale=0.9, toxicity_tighten=0.9,
                action=ResponseAction.SCALE_DOWN
            ),
            CrashSeverity.MODERATE: CrashResponse(
                severity=CrashSeverity.MODERATE,
                shotgun_scale=0.5, sniper_scale=0.7,
                max_clip_scale=0.8, toxicity_tighten=0.7,
                action=ResponseAction.SCALE_DOWN
            ),
            CrashSeverity.SEVERE: CrashResponse(
                severity=CrashSeverity.SEVERE,
                shotgun_scale=0.0, sniper_scale=0.2,
                max_clip_scale=0.5, toxicity_tighten=0.5,
                action=ResponseAction.SELECTIVE_HALT
            ),
            CrashSeverity.EXTREME: CrashResponse(
                severity=CrashSeverity.EXTREME,
                shotgun_scale=0.0, sniper_scale=0.0,
                max_clip_scale=0.0, toxicity_tighten=0.0,
                action=ResponseAction.EMERGENCY_HALT
            ),
            CrashSeverity.SYSTEMIC: CrashResponse(
                severity=CrashSeverity.SYSTEMIC,
                shotgun_scale=0.0, sniper_scale=0.0,
                max_clip_scale=0.0, toxicity_tighten=0.0,
                action=ResponseAction.LIQUIDATE
            )
        }
        
        # State tracking
        self.current_severity = CrashSeverity.NORMAL
        self.last_check_time = 0.0
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.severity_history: List[Tuple[float, CrashSeverity]] = []
        
        # Configuration
        self.check_interval_seconds = config.get("check_interval", 5.0)
        self.history_length = config.get("history_length", 300)  # 5 minutes at 1s intervals
        self.volatility_window = config.get("volatility_window", 60)  # 1 minute
        self.recovery_patience = config.get("recovery_patience", 30)   # 30s before recovery
        
        # Thresholds (in sigma units)
        self.thresholds = {
            CrashSeverity.MINOR: 1.5,
            CrashSeverity.MODERATE: 2.5,
            CrashSeverity.SEVERE: 3.5,
            CrashSeverity.EXTREME: 4.5
        }
        
        logger.info("🚨 Advanced Crash Sentinel ENABLED")
        logger.info(f"   Check interval: {self.check_interval_seconds}s")
        logger.info(f"   Volatility window: {self.volatility_window}s")
    
    def is_available(self) -> bool:
        """Check if advanced crash sentinel is available"""
        return self.enabled
    
    async def analyze_market_conditions(self, market_data: Dict[str, Any]) -> CrashSeverity:
        """
        Analyze current market conditions and determine crash severity.
        
        Returns severity level, or NORMAL if feature disabled.
        """
        if not self.enabled:
            return CrashSeverity.NORMAL
        
        try:
            current_time = time.time()
            
            # Skip if too soon since last check
            if current_time - self.last_check_time < self.check_interval_seconds:
                return self.current_severity
            
            self.last_check_time = current_time
            
            # Extract market data
            current_price = market_data.get("price", 0.0)
            current_volume = market_data.get("volume", 0.0)
            oracle_price = market_data.get("oracle_price", current_price)
            
            # Update history
            self._update_history(current_price, current_volume)
            
            # Calculate risk metrics
            condition = self._calculate_market_condition(current_price, current_volume, oracle_price)
            
            # Determine severity
            severity = self._determine_severity(condition)
            
            # Update current severity with smoothing
            if severity != self.current_severity:
                await self._handle_severity_change(severity, condition)
            
            return self.current_severity
            
        except Exception as e:
            logger.error(f"❌ Crash sentinel analysis failed: {e}")
            return CrashSeverity.NORMAL
    
    def _update_history(self, price: float, volume: float):
        """Update price and volume history"""
        self.price_history.append(price)
        self.volume_history.append(volume)
        
        # Trim history to maintain size
        if len(self.price_history) > self.history_length:
            self.price_history = self.price_history[-self.history_length:]
        if len(self.volume_history) > self.history_length:
            self.volume_history = self.volume_history[-self.history_length:]
    
    def _calculate_market_condition(self, current_price: float, current_volume: float, oracle_price: float) -> MarketCondition:
        """Calculate comprehensive market condition metrics"""
        
        if len(self.price_history) < 60:  # Need minimum history
            return MarketCondition(timestamp=time.time())
        
        prices = np.array(self.price_history)
        volumes = np.array(self.volume_history)
        
        # Price change analysis
        price_change_1m = (current_price - prices[-60]) / prices[-60] if len(prices) >= 60 else 0.0
        price_change_5m = (current_price - prices[-300]) / prices[-300] if len(prices) >= 300 else 0.0
        
        # Volume analysis
        avg_volume = np.mean(volumes[-60:]) if len(volumes) >= 60 else current_volume
        volume_spike = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Volatility analysis  
        returns = np.diff(prices[-self.volatility_window:]) / prices[-self.volatility_window:-1]
        current_volatility = np.std(returns) if len(returns) > 1 else 0.0
        historical_volatility = np.std(np.diff(prices) / prices[:-1]) if len(prices) > 1 else current_volatility
        volatility_spike = current_volatility / historical_volatility if historical_volatility > 0 else 1.0
        
        # Oracle deviation
        oracle_deviation = abs(current_price - oracle_price) / oracle_price if oracle_price > 0 else 0.0
        
        return MarketCondition(
            price_change_1m=price_change_1m,
            price_change_5m=price_change_5m,
            volume_spike=volume_spike,
            volatility_spike=volatility_spike,
            oracle_deviation=oracle_deviation,
            timestamp=time.time()
        )
    
    def _determine_severity(self, condition: MarketCondition) -> CrashSeverity:
        """Determine crash severity based on market conditions"""
        
        # Calculate composite risk score
        risk_factors = [
            abs(condition.price_change_1m) * 100,    # Price change as percentage
            abs(condition.price_change_5m) * 100,    # 5min price change
            max(0, condition.volume_spike - 1) * 2,  # Volume spike above normal
            max(0, condition.volatility_spike - 1),  # Volatility spike
            condition.oracle_deviation * 100        # Oracle deviation as percentage
        ]
        
        # Weight the factors
        weights = [3.0, 2.0, 1.0, 2.0, 1.5]  # Price changes weighted more heavily
        risk_score = sum(factor * weight for factor, weight in zip(risk_factors, weights))
        
        # Convert to sigma-equivalent (rough calibration)
        sigma_equivalent = risk_score / 5.0  # Tunable parameter
        
        # Determine severity level
        if sigma_equivalent >= self.thresholds[CrashSeverity.EXTREME]:
            return CrashSeverity.EXTREME
        elif sigma_equivalent >= self.thresholds[CrashSeverity.SEVERE]:
            return CrashSeverity.SEVERE
        elif sigma_equivalent >= self.thresholds[CrashSeverity.MODERATE]:
            return CrashSeverity.MODERATE
        elif sigma_equivalent >= self.thresholds[CrashSeverity.MINOR]:
            return CrashSeverity.MINOR
        else:
            return CrashSeverity.NORMAL
    
    async def _handle_severity_change(self, new_severity: CrashSeverity, condition: MarketCondition):
        """Handle changes in crash severity"""
        
        old_severity = self.current_severity
        
        # Require confirmation for severity increases (avoid false positives)
        if new_severity.value > old_severity.value:
            # Check if we've seen this severity recently
            recent_severities = [s for t, s in self.severity_history if time.time() - t < 30]
            if recent_severities.count(new_severity) < 2:  # Need 2 confirmations
                logger.info(f"🚨 Crash severity increase detected but not confirmed: {old_severity.value} -> {new_severity.value}")
                return
        
        # Update severity
        self.current_severity = new_severity
        self.severity_history.append((time.time(), new_severity))
        
        # Trim history
        self.severity_history = [(t, s) for t, s in self.severity_history if time.time() - t < 3600]
        
        # Log change
        if new_severity != old_severity:
            logger.warning(f"🚨 Crash severity changed: {old_severity.value} -> {new_severity.value}")
            logger.warning(f"   Price change 1m: {condition.price_change_1m:.2%}")
            logger.warning(f"   Volume spike: {condition.volume_spike:.1f}x")
            logger.warning(f"   Volatility spike: {condition.volatility_spike:.1f}x")
    
    def get_response_for_severity(self, severity: CrashSeverity) -> CrashResponse:
        """Get the response configuration for a given severity level"""
        if not self.enabled:
            return self.response_matrix[CrashSeverity.NORMAL]
        
        return self.response_matrix.get(severity, self.response_matrix[CrashSeverity.NORMAL])
    
    def get_current_scaling(self) -> Dict[str, float]:
        """Get current scaling factors for strategies"""
        if not self.enabled:
            return {"shotgun_scale": 1.0, "sniper_scale": 1.0, "clip_scale": 1.0}
        
        response = self.get_response_for_severity(self.current_severity)
        return {
            "shotgun_scale": response.shotgun_scale,
            "sniper_scale": response.sniper_scale,
            "clip_scale": response.max_clip_scale,
            "toxicity_scale": response.toxicity_tighten
        }
    
    def should_halt_strategy(self, strategy: StrategySource) -> bool:
        """Check if a specific strategy should be halted"""
        if not self.enabled:
            return False
        
        response = self.get_response_for_severity(self.current_severity)
        
        if strategy == StrategySource.SHOTGUN:
            return response.shotgun_scale == 0.0
        elif strategy == StrategySource.SNIPER:
            return response.sniper_scale == 0.0
        else:
            return response.action in [ResponseAction.EMERGENCY_HALT, ResponseAction.LIQUIDATE]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current crash sentinel status"""
        if not self.enabled:
            return {"feature_enabled": False}
        
        response = self.get_response_for_severity(self.current_severity)
        
        return {
            "feature_enabled": True,
            "current_severity": self.current_severity.value,
            "response_action": response.action.value,
            "scaling": {
                "shotgun": response.shotgun_scale,
                "sniper": response.sniper_scale,
                "clip_size": response.max_clip_scale,
                "toxicity": response.toxicity_tighten
            },
            "last_check": self.last_check_time,
            "history_length": len(self.price_history),
            "recent_severity_changes": len([s for t, s in self.severity_history if time.time() - t < 300])
        }
    
    async def force_severity(self, severity: CrashSeverity, duration_seconds: int = 300):
        """Manually force a severity level for testing/emergency"""
        if not self.enabled:
            return
        
        old_severity = self.current_severity
        self.current_severity = severity
        
        logger.warning(f"🚨 FORCED severity level: {severity.value} for {duration_seconds}s")
        
        # Restore after duration
        await asyncio.sleep(duration_seconds)
        self.current_severity = old_severity
        logger.info(f"🚨 Restored severity level: {old_severity.value}")




