from __future__ import annotations
import yaml
import time
import logging
from typing import Dict, Optional, List
from pathlib import Path

# Use existing Swift sidecar driver
from libs.drift.swift_sidecar_driver import SwiftSidecarDriver
from .types import ShotgunConfig, SniperConfig, to_sidecar_payload, Regime, AttributionData, StrategySource
from .allocation import AllocationManager

# Advanced features (only imported if feature flags enabled)
from .feature_flags import (
    get_feature_manager, has_advanced_toggle_manager, has_advanced_crash_sentinel,
    has_sophisticated_hedge_coupling, has_advanced_quality_filters,
    has_realtime_optimization, has_comprehensive_testing
)

# Conditional imports for advanced features
if has_advanced_toggle_manager():
    from .advanced.toggle_manager import AdvancedToggleManager
if has_advanced_crash_sentinel():
    from .advanced.crash_sentinel import AdvancedCrashSentinel
if has_sophisticated_hedge_coupling():
    from .advanced.hedge_coupling import SophisticatedHedgeCoupling
if has_advanced_quality_filters():
    from .advanced.quality_filters import AdvancedQualityFilters
if has_realtime_optimization():
    from .advanced.optimization import RealtimeOptimizer
if has_comprehensive_testing():
    from .advanced.testing_framework import ComprehensiveTestingFramework

logger = logging.getLogger("jitter.hybrid")

class HybridJitter:
    """
    Clean, production-ready Hybrid Jitter implementation that integrates
    with existing Swift sidecar infrastructure while adding attribution
    and performance tracking capabilities.
    
    Key improvements over the complex implementation:
    1. Uses existing SwiftSidecarDriver vs custom TypeScript service
    2. Control-plane only (no hot data-plane interference)
    3. Clean configuration management
    4. Built-in attribution for performance analysis
    5. Integrates seamlessly with orchestrator
    """
    
    def __init__(self, 
                 sidecar: SwiftSidecarDriver,
                 shotgun_cfg_path: str = "configs/jitter/shotgun.yaml",
                 sniper_cfg_path: str = "configs/jitter/sniper.yaml",
                 alloc_cfg_path: str = "configs/regime/jitter_allocation.yaml"):
        
        self.sidecar = sidecar
        self.shotgun_cfg = self._load_yaml(shotgun_cfg_path, ShotgunConfig)
        self.sniper_cfg = self._load_yaml(sniper_cfg_path, SniperConfig)
        
        # Load allocation table
        with open(alloc_cfg_path, "r") as fh:
            table = yaml.safe_load(fh)
        self.alloc = AllocationManager(table)
        
        # Attribution tracking
        self.fills: List[AttributionData] = []
        self.performance_metrics = {}
        self.last_config_push = 0.0
        
        # Initialize advanced features (only if enabled)
        self.advanced_features = {}
        self._initialize_advanced_features()
        
        logger.info("🚀 HybridJitter initialized with clean architecture")
        logger.info(f"   Shotgun: {self.shotgun_cfg.clip_size} SOL clips, {self.shotgun_cfg.toxicity_max:.2f} toxicity max")
        logger.info(f"   Sniper: {self.sniper_cfg.clip_size} SOL clips, {self.sniper_cfg.toxicity_max:.2f} toxicity max")
        
        # Log enabled advanced features
        enabled_features = [name for name, feature in self.advanced_features.items() if feature is not None]
        if enabled_features:
            logger.info(f"✨ Advanced features enabled: {', '.join(enabled_features)}")
        else:
            logger.info("🛡️ Running in SIMPLE mode (all advanced features disabled)")

    def _load_yaml(self, path: str, cls):
        """Safely load YAML configuration into dataclass"""
        if not Path(path).exists():
            logger.warning(f"Config file {path} not found, using defaults")
            return cls()
            
        with open(path, "r") as fh:
            raw = yaml.safe_load(fh) or {}
        
        # Safely map YAML to dataclass
        kwargs = {}
        for field_name in cls.__dataclass_fields__:
            if field_name in raw:
                kwargs[field_name] = raw[field_name]
        
        obj = cls(**kwargs)
        
        # Handle nested auction config
        if "auction" in raw and hasattr(obj, "auction"):
            auction_data = raw["auction"]
            for key, value in auction_data.items():
                if hasattr(obj.auction, key):
                    setattr(obj.auction, key, value)
        
        return obj

    def _initialize_advanced_features(self):
        """Initialize advanced features based on feature flags"""
        
        # Initialize toggle manager
        if has_advanced_toggle_manager():
            try:
                self.advanced_features["toggle_manager"] = AdvancedToggleManager({})
                logger.info("🔄 Advanced Toggle Manager initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize toggle manager: {e}")
                self.advanced_features["toggle_manager"] = None
        else:
            self.advanced_features["toggle_manager"] = None
        
        # Initialize crash sentinel
        if has_advanced_crash_sentinel():
            try:
                self.advanced_features["crash_sentinel"] = AdvancedCrashSentinel({})
                logger.info("🚨 Advanced Crash Sentinel initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize crash sentinel: {e}")
                self.advanced_features["crash_sentinel"] = None
        else:
            self.advanced_features["crash_sentinel"] = None
        
        # Initialize hedge coupling
        if has_sophisticated_hedge_coupling():
            try:
                self.advanced_features["hedge_coupling"] = SophisticatedHedgeCoupling({})
                logger.info("⚖️ Sophisticated Hedge Coupling initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize hedge coupling: {e}")
                self.advanced_features["hedge_coupling"] = None
        else:
            self.advanced_features["hedge_coupling"] = None
        
        # Initialize quality filters
        if has_advanced_quality_filters():
            try:
                self.advanced_features["quality_filters"] = AdvancedQualityFilters({})
                logger.info("🔍 Advanced Quality Filters initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize quality filters: {e}")
                self.advanced_features["quality_filters"] = None
        else:
            self.advanced_features["quality_filters"] = None
        
        # Initialize real-time optimization
        if has_realtime_optimization():
            try:
                self.advanced_features["optimization"] = RealtimeOptimizer({})
                logger.info("📊 Real-time Optimization initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize optimization: {e}")
                self.advanced_features["optimization"] = None
        else:
            self.advanced_features["optimization"] = None
        
        # Initialize testing framework
        if has_comprehensive_testing():
            try:
                self.advanced_features["testing"] = ComprehensiveTestingFramework({})
                logger.info("🧪 Comprehensive Testing Framework initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize testing framework: {e}")
                self.advanced_features["testing"] = None
        else:
            self.advanced_features["testing"] = None

    def apply_for_regime(self, regime: Regime) -> Dict[str, float]:
        """
        Apply jitter configuration for the given regime.
        This is the main method called by the orchestrator on regime changes.
        
        Returns the allocation weights for attribution/monitoring.
        """
        try:
            # Get regime-appropriate weights (maintains exact ratios from requirements)
            weights = self.alloc.weights_for(regime)
            
            # Create sidecar payload
            payload = to_sidecar_payload(self.shotgun_cfg, self.sniper_cfg, weights)
            
            # Push to TypeScript sidecar (control-plane, not latency critical)
            self._push_config_to_sidecar(payload)
            
            # Log regime change for monitoring
            logger.info(f"📊 Applied {regime} regime allocation:")
            logger.info(f"   Shotgun: {weights['shotgun']:.1%} (clips: {self.shotgun_cfg.clip_size} SOL)")
            logger.info(f"   Sniper:  {weights['sniper']:.1%} (clips: {self.sniper_cfg.clip_size} SOL)")
            
            return weights
            
        except Exception as e:
            logger.error(f"❌ Failed to apply regime {regime}: {e}")
            raise

    def _push_config_to_sidecar(self, payload: Dict):
        """Push configuration to TypeScript sidecar via /control/jitter endpoint"""
        try:
            # Use the existing Swift sidecar driver to push config
            # Note: We need to add this endpoint to the TypeScript sidecar
            response = self.sidecar._client.post(
                f"{self.sidecar.base_url}/control/jitter", 
                json=payload,
                headers=self.sidecar._headers()
            )
            response.raise_for_status()
            
            self.last_config_push = time.time()
            logger.debug(f"✅ Config pushed to sidecar: {response.status_code}")
            
        except Exception as e:
            logger.error(f"❌ Failed to push config to sidecar: {e}")
            # Don't raise - this is control plane, not critical path
            
    # Operator convenience methods for live control
    def set_shotgun_enabled(self, enabled: bool):
        """Enable/disable shotgun strategy"""
        self.shotgun_cfg.enabled = enabled
        current_regime = self.alloc.get_current_regime()
        weights = self.alloc.weights_for(current_regime)
        payload = to_sidecar_payload(self.shotgun_cfg, self.sniper_cfg, weights)
        self._push_config_to_sidecar(payload)
        logger.info(f"🔫 Shotgun {'enabled' if enabled else 'disabled'}")

    def set_sniper_enabled(self, enabled: bool):
        """Enable/disable sniper strategy"""
        self.sniper_cfg.enabled = enabled
        current_regime = self.alloc.get_current_regime()
        weights = self.alloc.weights_for(current_regime)
        payload = to_sidecar_payload(self.shotgun_cfg, self.sniper_cfg, weights)
        self._push_config_to_sidecar(payload)
        logger.info(f"🎯 Sniper {'enabled' if enabled else 'disabled'}")
        
    def set_clip_sizes(self, shotgun_size: Optional[float] = None, sniper_size: Optional[float] = None):
        """Dynamically adjust clip sizes"""
        if shotgun_size is not None:
            self.shotgun_cfg.clip_size = shotgun_size
            logger.info(f"🔫 Shotgun clip size: {shotgun_size} SOL")
        if sniper_size is not None:
            self.sniper_cfg.clip_size = sniper_size
            logger.info(f"🎯 Sniper clip size: {sniper_size} SOL")
            
        # Re-apply current configuration
        current_regime = self.alloc.get_current_regime()
        self.apply_for_regime(current_regime)
        
    def emergency_halt(self):
        """Emergency halt all jitter strategies"""
        logger.warning("🚨 EMERGENCY HALT: Disabling all jitter strategies")
        self.shotgun_cfg.enabled = False
        self.sniper_cfg.enabled = False
        weights = {"shotgun": 0.0, "sniper": 0.0, "regime": "crash", "timestamp": time.time()}
        payload = to_sidecar_payload(self.shotgun_cfg, self.sniper_cfg, weights)
        self._push_config_to_sidecar(payload)

    # Attribution and performance tracking
    def record_fill(self, fill_data: Dict):
        """Record a fill for attribution analysis"""
        try:
            attribution = AttributionData(
                source=StrategySource(fill_data.get("source", "shotgun")),
                fill_id=fill_data.get("fill_id", f"fill_{int(time.time())}"),
                timestamp=fill_data.get("timestamp", time.time()),
                market=fill_data.get("market", "SOL-PERP"),
                side=fill_data.get("side", "buy"),
                size=fill_data.get("size", 0.0),
                price=fill_data.get("price", 0.0),
                pnl=fill_data.get("pnl"),
                latency_ms=fill_data.get("latency_ms"),
                regime=self.alloc.get_current_regime()
            )
            
            self.fills.append(attribution)
            
            # Limit memory usage
            if len(self.fills) > 10000:
                self.fills = self.fills[-5000:]
                
            logger.debug(f"📊 Recorded {attribution.source.value} fill: {attribution.size:.3f} @ ${attribution.price:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to record fill: {e}")

    def get_performance_summary(self) -> Dict:
        """Get performance summary for monitoring"""
        if not self.fills:
            return {"status": "no_data"}
        
        # Calculate basic metrics by source
        shotgun_fills = [f for f in self.fills if f.source == StrategySource.SHOTGUN]
        sniper_fills = [f for f in self.fills if f.source == StrategySource.SNIPER]
        
        summary = {
            "total_fills": len(self.fills),
            "shotgun": {
                "fills": len(shotgun_fills),
                "volume": sum(f.size for f in shotgun_fills),
                "avg_size": sum(f.size for f in shotgun_fills) / max(len(shotgun_fills), 1)
            },
            "sniper": {
                "fills": len(sniper_fills),
                "volume": sum(f.size for f in sniper_fills),
                "avg_size": sum(f.size for f in sniper_fills) / max(len(sniper_fills), 1)
            },
            "current_regime": self.alloc.get_current_regime(),
            "last_config_push": self.last_config_push,
            "shotgun_enabled": self.shotgun_cfg.enabled,
            "sniper_enabled": self.sniper_cfg.enabled
        }
        
        return summary

    def get_allocation_history(self) -> List:
        """Get allocation history for analysis"""
        return self.alloc.get_allocation_history()
        
    def get_current_config(self) -> Dict:
        """Get current configuration for debugging"""
        return {
            "shotgun": {
                "enabled": self.shotgun_cfg.enabled,
                "clip_size": self.shotgun_cfg.clip_size,
                "toxicity_max": self.shotgun_cfg.toxicity_max,
                "markets": self.shotgun_cfg.markets
            },
            "sniper": {
                "enabled": self.sniper_cfg.enabled,
                "clip_size": self.sniper_cfg.clip_size,
                "toxicity_max": self.sniper_cfg.toxicity_max,
                "markets": self.sniper_cfg.markets
            },
            "current_regime": self.alloc.get_current_regime()
        }
