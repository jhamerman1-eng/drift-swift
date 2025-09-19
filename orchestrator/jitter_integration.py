"""
Clean Jitter Integration for Orchestrator

This is a drop-in integration that plugs the Hybrid Jitter system
into your existing orchestrator with minimal changes.
"""

import logging
import asyncio
from typing import Dict, Any, Optional

from libs.drift.swift_sidecar_driver import SwiftSidecarDriver  
from libs.jitter.hybrid import HybridJitter
from libs.jitter.types import Regime

logger = logging.getLogger("orchestrator.jitter")

class JitterOrchestrator:
    """
    Clean integration between regime detection and jitter strategies.
    Plugs into existing orchestrator infrastructure.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.jitter: Optional[HybridJitter] = None
        self.metrics = None  # Will be set by orchestrator
        self.running = False
        
        # Initialize Swift sidecar connection
        sidecar_config = config.get("jit", {}).get("sidecar", {})
        host = sidecar_config.get("host", "localhost")
        port = sidecar_config.get("port", 8787)
        
        self.swift_sidecar = SwiftSidecarDriver(
            base_url=f"http://{host}:{port}",
            timeout_s=10.0
        )
        
        # Initialize jitter system
        self.jitter = HybridJitter(self.swift_sidecar)
        
        logger.info("🚀 JitterOrchestrator initialized")
        
    async def start(self):
        """Start the jitter orchestrator"""
        if not self.jitter:
            logger.error("❌ Jitter not initialized")
            return
            
        try:
            # Test sidecar connectivity
            health = self.swift_sidecar.health()
            logger.info(f"✅ Sidecar health: {health.get('status', 'unknown')}")
            
            # Apply initial regime (calm by default)
            initial_weights = self.jitter.apply_for_regime("calm")
            logger.info(f"📊 Initial allocation: {initial_weights}")
            
            self.running = True
            logger.info("✅ JitterOrchestrator started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start JitterOrchestrator: {e}")
            raise
    
    async def stop(self):
        """Stop the jitter orchestrator"""
        if self.jitter:
            self.jitter.emergency_halt()
        self.running = False
        logger.info("🛑 JitterOrchestrator stopped")
    
    async def on_regime_change(self, new_regime: str):
        """
        Handle regime changes from the regime detector.
        This is the main integration point with your existing orchestrator.
        """
        if not self.jitter or not self.running:
            return
            
        try:
            # Map regime string to our type system
            regime_mapping = {
                "calm": "calm",
                "normal": "calm",  # Map normal to calm for now
                "trend": "trend", 
                "trending": "trend",
                "volatile": "volatile",
                "crash": "crash",
                "emergency": "crash"
            }
            
            mapped_regime = regime_mapping.get(new_regime.lower(), "calm")
            
            logger.info(f"🔄 Regime change: {new_regime} -> {mapped_regime}")
            
            # Crash Sentinel integration - crash has ultimate veto
            if mapped_regime == "crash":
                logger.warning("🚨 CRASH REGIME: Emergency halt all jitter")
                self.jitter.emergency_halt()
                
                # Also disable Swift sidecar allowlist if available
                try:
                    # TODO: Add this endpoint to sidecar if needed
                    # self.swift_sidecar.set_allowlist([])
                    pass
                except Exception as e:
                    logger.warning(f"Could not disable sidecar allowlist: {e}")
                return
            
            # Normal regime change - apply new allocation
            weights = self.jitter.apply_for_regime(mapped_regime)
            
            # Update metrics if available
            if self.metrics:
                self.metrics.gauge("jitter_shotgun_weight", weights["shotgun"])
                self.metrics.gauge("jitter_sniper_weight", weights["sniper"])
                self.metrics.gauge("jitter_regime_numeric", self._regime_to_numeric(mapped_regime))
            
            logger.info(f"✅ Applied {mapped_regime} allocation: Shotgun {weights['shotgun']:.1%}, Sniper {weights['sniper']:.1%}")
            
        except Exception as e:
            logger.error(f"❌ Failed to handle regime change: {e}")
    
    def on_fill(self, fill_data: Dict[str, Any]):
        """
        Handle fill events for attribution.
        This can be called by your existing fill processing logic.
        """
        if not self.jitter:
            return
            
        try:
            # Record fill for attribution
            self.jitter.record_fill(fill_data)
            
            # TODO: Route delta to hedge bot with source attribution
            # Example: self.hedge.consume_fill(fill_data, source=fill_data.get("source", "unknown"))
            
        except Exception as e:
            logger.error(f"❌ Failed to process fill: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring/dashboards"""
        if not self.jitter:
            return {"error": "jitter_not_initialized"}
        
        return self.jitter.get_performance_summary()
    
    def get_current_config(self) -> Dict[str, Any]:
        """Get current jitter configuration"""
        if not self.jitter:
            return {"error": "jitter_not_initialized"}
        
        return self.jitter.get_current_config()
    
    # Operator controls for live management
    def enable_shotgun(self, enabled: bool = True):
        """Enable/disable shotgun strategy"""
        if self.jitter:
            self.jitter.set_shotgun_enabled(enabled)
    
    def enable_sniper(self, enabled: bool = True):
        """Enable/disable sniper strategy"""
        if self.jitter:
            self.jitter.set_sniper_enabled(enabled)
    
    def set_clip_sizes(self, shotgun_size: Optional[float] = None, sniper_size: Optional[float] = None):
        """Adjust clip sizes dynamically"""
        if self.jitter:
            self.jitter.set_clip_sizes(shotgun_size, sniper_size)
    
    def emergency_halt(self):
        """Emergency halt all strategies"""
        if self.jitter:
            self.jitter.emergency_halt()
    
    def _regime_to_numeric(self, regime: str) -> float:
        """Convert regime to numeric for metrics"""
        regime_map = {
            "calm": 1.0,
            "trend": 2.0, 
            "volatile": 3.0,
            "crash": 4.0
        }
        return regime_map.get(regime, 0.0)

# Integration snippet for master orchestrator
"""
# orchestrator/master.py - Integration example

class MasterOrchestrator:
    def __init__(self, cfg):
        self.cfg = cfg
        
        # Initialize jitter orchestrator
        self.jitter_orchestrator = JitterOrchestrator(cfg)
        
        # Set metrics reference if you have one
        # self.jitter_orchestrator.metrics = self.metrics

    async def start(self):
        # Start jitter orchestrator
        await self.jitter_orchestrator.start()
        
        # ... other startup logic

    async def on_regime_change(self, new_regime: str):
        # Route to jitter orchestrator
        await self.jitter_orchestrator.on_regime_change(new_regime)
        
        # ... other regime change logic

    def on_fill(self, fill):
        # Route fill to jitter for attribution
        self.jitter_orchestrator.on_fill(fill)
        
        # Route delta to hedge; tag by source for attribution  
        source = fill.get("source", "unknown")
        self.hedge.consume_fill(fill, source=source)
"""




