#!/usr/bin/env python3
"""
Enhanced Position and Size Logging System
Provides detailed logging for position tracking, size calculations, and margin management
"""

import asyncio
import logging
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

from driftpy.constants.numeric_constants import QUOTE_PRECISION, BASE_PRECISION
from driftpy.math.margin import MarginCategory

class PositionLogger:
    """Enhanced position logging system"""
    
    def __init__(self, log_file: str = "position_analysis.log"):
        self.log_file = log_file
        self.position_history = []
        self.size_history = []
        self.collateral_history = []
        self.error_history = []
        
        # Setup logging
        self.logger = logging.getLogger("position-logger")
        self.logger.setLevel(logging.DEBUG)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_position_update(self, old_position: float, new_position: float, 
                          max_position: float, source: str = "unknown"):
        """Log position update with detailed analysis"""
        position_change = new_position - old_position
        utilization = abs(new_position) / max_position * 100
        
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "old_position": old_position,
            "new_position": new_position,
            "position_change": position_change,
            "max_position": max_position,
            "utilization": utilization,
            "source": source,
            "should_trade": abs(new_position) < max_position
        }
        
        self.position_history.append(log_data)
        
        # Log the update
        self.logger.info(f"🔄 Position Update: {old_position:.6f} → {new_position:.6f} SOL")
        self.logger.info(f"   Change: {position_change:+.6f} SOL")
        self.logger.info(f"   Utilization: {utilization:.2f}%")
        self.logger.info(f"   Should Trade: {log_data['should_trade']}")
        self.logger.info(f"   Source: {source}")
        
        # Warning if position is near limits
        if utilization > 90:
            self.logger.warning(f"⚠️ High position utilization: {utilization:.2f}%")
        elif utilization > 100:
            self.logger.error(f"🚨 Position limit exceeded: {utilization:.2f}%")
    
    def log_size_calculation(self, position: float, max_position: float, 
                           base_size: float, calculated_size: float, 
                           reason: str = ""):
        """Log size calculation with reasoning"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "position": position,
            "max_position": max_position,
            "base_size": base_size,
            "calculated_size": calculated_size,
            "reason": reason,
            "position_utilization": abs(position) / max_position * 100
        }
        
        self.size_history.append(log_data)
        
        self.logger.info(f"📏 Size Calculation:")
        self.logger.info(f"   Position: {position:.6f} SOL")
        self.logger.info(f"   Max Position: {max_position:.6f} SOL")
        self.logger.info(f"   Base Size: {base_size:.6f} SOL")
        self.logger.info(f"   Calculated Size: {calculated_size:.6f} SOL")
        self.logger.info(f"   Reason: {reason}")
        
        if calculated_size == 0 and position < max_position:
            self.logger.warning(f"⚠️ Size is 0 but position is within limits!")
    
    def log_collateral_status(self, total_collateral: float, free_collateral: float, 
                            margin_requirement: float, utilization: float):
        """Log collateral status"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "total_collateral": total_collateral,
            "free_collateral": free_collateral,
            "margin_requirement": margin_requirement,
            "utilization": utilization
        }
        
        self.collateral_history.append(log_data)
        
        self.logger.info(f"💰 Collateral Status:")
        self.logger.info(f"   Total: ${total_collateral:.2f}")
        self.logger.info(f"   Free: ${free_collateral:.2f}")
        self.logger.info(f"   Margin Req: ${margin_requirement:.2f}")
        self.logger.info(f"   Utilization: {utilization:.1f}%")
        
        if free_collateral < 50:
            self.logger.warning(f"⚠️ Low free collateral: ${free_collateral:.2f}")
        if utilization > 80:
            self.logger.warning(f"⚠️ High collateral utilization: {utilization:.1f}%")
    
    def log_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """Log errors with context"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        }
        
        self.error_history.append(log_data)
        
        self.logger.error(f"❌ Error: {error_type}")
        self.logger.error(f"   Message: {error_message}")
        if context:
            self.logger.error(f"   Context: {json.dumps(context, indent=2)}")
    
    def log_order_decision(self, side: str, position: float, max_position: float, 
                          size: float, reason: str, approved: bool):
        """Log order placement decision"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "side": side,
            "position": position,
            "max_position": max_position,
            "size": size,
            "reason": reason,
            "approved": approved
        }
        
        self.logger.info(f"🎯 Order Decision: {side.upper()}")
        self.logger.info(f"   Position: {position:.6f} SOL")
        self.logger.info(f"   Size: {size:.6f} SOL")
        self.logger.info(f"   Reason: {reason}")
        self.logger.info(f"   Approved: {'✅' if approved else '❌'}")
        
        if not approved:
            self.logger.warning(f"⚠️ Order rejected: {reason}")
    
    def generate_position_report(self) -> Dict[str, Any]:
        """Generate comprehensive position report"""
        if not self.position_history:
            return {"error": "No position data available"}
        
        # Calculate statistics
        positions = [p["new_position"] for p in self.position_history]
        changes = [p["position_change"] for p in self.position_history]
        utilizations = [p["utilization"] for p in self.position_history]
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_updates": len(self.position_history),
                "current_position": positions[-1] if positions else 0,
                "min_position": min(positions) if positions else 0,
                "max_position": max(positions) if positions else 0,
                "avg_position": sum(positions) / len(positions) if positions else 0,
                "total_changes": sum(changes),
                "avg_utilization": sum(utilizations) / len(utilizations) if utilizations else 0
            },
            "recent_positions": self.position_history[-10:],
            "recent_sizes": self.size_history[-10:],
            "recent_collateral": self.collateral_history[-10:],
            "errors": self.error_history[-5:]
        }
        
        return report
    
    def save_report(self, filename: str = None):
        """Save position report to file"""
        if filename is None:
            filename = f"position_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = self.generate_position_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"📊 Position report saved to: {filename}")
        return filename

class EnhancedPositionTracker:
    """Enhanced position tracker with comprehensive logging"""
    
    def __init__(self, max_position: float = 120.0, log_file: str = "position_analysis.log"):
        self.max_position = max_position
        self.current_position = 0.0
        self.position_logger = PositionLogger(log_file)
        self.update_count = 0
        
    def update_position(self, new_position: float, source: str = "driftpy"):
        """Update position with enhanced logging"""
        old_position = self.current_position
        self.current_position = new_position
        self.update_count += 1
        
        # Log the update
        self.position_logger.log_position_update(
            old_position, new_position, self.max_position, source
        )
        
        # Log size calculation
        base_size = 0.01  # SOL
        if abs(new_position) >= self.max_position:
            calculated_size = 0.0
            reason = f"Position limit reached: {abs(new_position):.6f} >= {self.max_position:.6f}"
        else:
            calculated_size = base_size
            reason = f"Position within limits: {abs(new_position):.6f} < {self.max_position:.6f}"
        
        self.position_logger.log_size_calculation(
            new_position, self.max_position, base_size, calculated_size, reason
        )
        
        return new_position
    
    def should_trade(self, position: float = None) -> bool:
        """Check if we should trade with logging"""
        if position is None:
            position = self.current_position
        
        should_trade = abs(position) < self.max_position
        
        # Log the decision
        reason = f"Position {position:.6f} {'within' if should_trade else 'exceeds'} limits"
        self.position_logger.log_order_decision(
            "check", position, self.max_position, 0.01, reason, should_trade
        )
        
        return should_trade
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return {
            "current_position": self.current_position,
            "max_position": self.max_position,
            "utilization": abs(self.current_position) / self.max_position * 100,
            "should_trade": self.should_trade(),
            "update_count": self.update_count
        }

async def test_enhanced_logging():
    """Test the enhanced logging system"""
    logger = logging.getLogger("test")
    logger.info("🧪 Testing Enhanced Position Logging")
    
    # Create tracker
    tracker = EnhancedPositionTracker(max_position=120.0)
    
    # Test various position scenarios
    test_positions = [
        (0.0, "initial"),
        (0.5, "small_positive"),
        (-0.5, "small_negative"),
        (119.0, "near_max"),
        (120.0, "at_max"),
        (121.0, "over_max"),
        (-119.0, "near_negative_max"),
        (-120.0, "at_negative_max"),
        (0.0, "reset")
    ]
    
    for position, source in test_positions:
        logger.info(f"\n--- Testing Position: {position} ({source}) ---")
        tracker.update_position(position, source)
        
        status = tracker.get_status()
        logger.info(f"Status: {status}")
        
        await asyncio.sleep(0.1)
    
    # Generate and save report
    report_file = tracker.position_logger.save_report()
    logger.info(f"📊 Report saved to: {report_file}")
    
    return report_file

if __name__ == "__main__":
    asyncio.run(test_enhanced_logging())

















