#!/usr/bin/env python3
"""
MM Bot Position Monitoring Script
Monitors position updates, size calculations, and trading decisions
"""

import asyncio
import logging
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("mm-monitor")

class MMBotMonitor:
    """Monitor for MM bot position and trading behavior"""
    
    def __init__(self):
        self.position_history = []
        self.trade_history = []
        self.error_history = []
        self.start_time = time.time()
        
    def log_position_update(self, old_position: float, new_position: float, 
                          max_position: float, should_trade: bool, source: str = "unknown"):
        """Log position update with analysis"""
        position_change = new_position - old_position
        utilization = abs(new_position) / max_position * 100
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "old_position": old_position,
            "new_position": new_position,
            "position_change": position_change,
            "max_position": max_position,
            "utilization": utilization,
            "should_trade": should_trade,
            "source": source
        }
        
        self.position_history.append(log_entry)
        
        # Log the update
        logger.info(f"🔄 Position Update: {old_position:.6f} -> {new_position:.6f} SOL")
        logger.info(f"   Change: {position_change:+.6f} SOL")
        logger.info(f"   Utilization: {utilization:.2f}%")
        logger.info(f"   Should Trade: {should_trade}")
        logger.info(f"   Source: {source}")
        
        # Check for anomalies
        if abs(new_position) > 1000:
            logger.error(f"🚨 ABNORMAL POSITION: {new_position:.6f} SOL")
            self.log_error("ABNORMAL_POSITION", f"Position {new_position:.6f} is abnormally large", log_entry)
        elif new_position == -5000.0 or new_position == 5000.0:
            logger.error(f"🚨 ERROR POSITION: {new_position:.6f} SOL - appears to be default/error value")
            self.log_error("ERROR_POSITION", f"Position {new_position:.6f} appears to be error value", log_entry)
        elif utilization > 90:
            logger.warning(f"⚠️ High position utilization: {utilization:.2f}%")
        elif utilization > 100:
            logger.error(f"🚨 Position limit exceeded: {utilization:.2f}%")
            self.log_error("POSITION_LIMIT_EXCEEDED", f"Position {new_position:.6f} exceeds limit {max_position:.6f}", log_entry)
    
    def log_trade_decision(self, side: str, price: float, size: float, 
                          position: float, max_position: float, reason: str, approved: bool):
        """Log trading decision"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "side": side,
            "price": price,
            "size": size,
            "position": position,
            "max_position": max_position,
            "reason": reason,
            "approved": approved
        }
        
        self.trade_history.append(log_entry)
        
        status = "✅ APPROVED" if approved else "❌ REJECTED"
        logger.info(f"🎯 Trade Decision: {side.upper()} {size:.6f} SOL @ ${price:.4f}")
        logger.info(f"   Position: {position:.6f} SOL (max: {max_position:.6f})")
        logger.info(f"   Reason: {reason}")
        logger.info(f"   Status: {status}")
        
        if not approved:
            logger.warning(f"⚠️ Trade rejected: {reason}")
    
    def log_error(self, error_type: str, message: str, context: dict = None):
        """Log error with context"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": message,
            "context": context or {}
        }
        
        self.error_history.append(log_entry)
        logger.error(f"❌ Error: {error_type} - {message}")
    
    def generate_report(self) -> dict:
        """Generate comprehensive monitoring report"""
        if not self.position_history:
            return {"error": "No position data available"}
        
        # Calculate statistics
        positions = [p["new_position"] for p in self.position_history]
        changes = [p["position_change"] for p in self.position_history]
        utilizations = [p["utilization"] for p in self.position_history]
        
        # Count errors
        error_counts = {}
        for error in self.error_history:
            error_type = error["error_type"]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Count trade decisions
        trade_counts = {"approved": 0, "rejected": 0}
        for trade in self.trade_history:
            if trade["approved"]:
                trade_counts["approved"] += 1
            else:
                trade_counts["rejected"] += 1
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "monitoring_duration": time.time() - self.start_time,
            "summary": {
                "total_position_updates": len(self.position_history),
                "current_position": positions[-1] if positions else 0,
                "min_position": min(positions) if positions else 0,
                "max_position": max(positions) if positions else 0,
                "avg_position": sum(positions) / len(positions) if positions else 0,
                "total_position_changes": sum(changes),
                "avg_utilization": sum(utilizations) / len(utilizations) if utilizations else 0,
                "total_errors": len(self.error_history),
                "error_types": error_counts,
                "total_trades": len(self.trade_history),
                "trade_approval_rate": trade_counts["approved"] / len(self.trade_history) * 100 if self.trade_history else 0
            },
            "recent_positions": self.position_history[-10:],
            "recent_trades": self.trade_history[-10:],
            "recent_errors": self.error_history[-5:],
            "anomalies": self._detect_anomalies()
        }
        
        return report
    
    def _detect_anomalies(self) -> list:
        """Detect anomalies in position data"""
        anomalies = []
        
        for i, pos in enumerate(self.position_history):
            # Check for large position changes
            if i > 0:
                prev_pos = self.position_history[i-1]["new_position"]
                change = abs(pos["new_position"] - prev_pos)
                if change > 10:  # More than 10 SOL change
                    anomalies.append({
                        "type": "LARGE_POSITION_CHANGE",
                        "timestamp": pos["timestamp"],
                        "change": change,
                        "from": prev_pos,
                        "to": pos["new_position"]
                    })
            
            # Check for abnormal position values
            if abs(pos["new_position"]) > 1000:
                anomalies.append({
                    "type": "ABNORMAL_POSITION",
                    "timestamp": pos["timestamp"],
                    "position": pos["new_position"]
                })
            
            # Check for error values
            if pos["new_position"] in [-5000.0, 5000.0]:
                anomalies.append({
                    "type": "ERROR_POSITION_VALUE",
                    "timestamp": pos["timestamp"],
                    "position": pos["new_position"]
                })
        
        return anomalies
    
    def save_report(self, filename: str = None):
        """Save monitoring report to file"""
        if filename is None:
            filename = f"mm_bot_monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = self.generate_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Monitoring report saved to: {filename}")
        return filename

# Global monitor instance
monitor = MMBotMonitor()

def log_position_update(old_position: float, new_position: float, 
                       max_position: float, should_trade: bool, source: str = "unknown"):
    """Global function to log position updates"""
    monitor.log_position_update(old_position, new_position, max_position, should_trade, source)

def log_trade_decision(side: str, price: float, size: float, 
                      position: float, max_position: float, reason: str, approved: bool):
    """Global function to log trade decisions"""
    monitor.log_trade_decision(side, price, size, position, max_position, reason, approved)

def log_error(error_type: str, message: str, context: dict = None):
    """Global function to log errors"""
    monitor.log_error(error_type, message, context)

def generate_report():
    """Generate monitoring report"""
    return monitor.generate_report()

def save_report(filename: str = None):
    """Save monitoring report"""
    return monitor.save_report(filename)

async def test_monitoring():
    """Test the monitoring system"""
    logger.info("🧪 Testing MM Bot Monitoring System")
    
    # Test position updates
    test_positions = [
        (0.0, 0.5, 120.0, True, "test"),
        (0.5, -0.3, 120.0, True, "test"),
        (-0.3, 119.0, 120.0, True, "test"),
        (119.0, 120.0, 120.0, False, "test"),
        (120.0, -5000.0, 120.0, False, "test"),  # This should trigger an error
        (-5000.0, 0.0, 120.0, True, "test"),  # This should trigger an error
    ]
    
    for old_pos, new_pos, max_pos, should_trade, source in test_positions:
        log_position_update(old_pos, new_pos, max_pos, should_trade, source)
        await asyncio.sleep(0.1)
    
    # Test trade decisions
    test_trades = [
        ("buy", 242.50, 0.01, 0.0, 120.0, "Normal trade", True),
        ("sell", 242.60, 0.01, 0.0, 120.0, "Normal trade", True),
        ("buy", 242.50, 0.01, 120.0, 120.0, "Position limit reached", False),
        ("sell", 242.60, 0.01, -120.0, 120.0, "Position limit reached", False),
    ]
    
    for side, price, size, position, max_pos, reason, approved in test_trades:
        log_trade_decision(side, price, size, position, max_pos, reason, approved)
        await asyncio.sleep(0.1)
    
    # Generate and save report
    report_file = save_report()
    logger.info(f"✅ Monitoring test complete. Report saved to: {report_file}")

if __name__ == "__main__":
    asyncio.run(test_monitoring())
















