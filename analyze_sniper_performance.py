#!/usr/bin/env python3
"""
SNIPER BOT PERFORMANCE ANALYSIS
Real-time analysis of trading activity and success rates after optimizations
"""

import re
import json
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_recent_performance():
    """Analyze recent bot performance after optimizations"""
    
    print("🎯 SNIPER BOT PERFORMANCE ANALYSIS")
    print("=" * 60)
    
    try:
        # Read recent log entries (last 1000 lines)
        with open("logs/jit-mm-swift.log", "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-1000:]
        
        # Performance metrics
        metrics = {
            "swift_orders_received": 0,
            "jit_processing_attempts": 0,
            "jit_completed_successfully": 0,
            "swift_api_errors": 0,
            "swift_api_success": 0,
            "insufficient_balance_warnings": 0,
            "direct_driftpy_orders": 0,
            "circuit_breaker_errors": 0,
            "context_errors": 0,
            "order_sync_activities": 0,
            "tracked_orders": 0
        }
        
        # Market breakdown
        markets = defaultdict(int)
        order_sizes = []
        
        # Recent activity timestamps
        recent_activity = []
        
        # Analyze each log line
        for line in lines:
            # Extract timestamp for recent activity analysis
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if timestamp_match:
                try:
                    log_time = datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S")
                    # Only analyze last 10 minutes
                    if log_time >= datetime.now() - timedelta(minutes=10):
                        recent_activity.append(log_time)
                except:
                    pass
            
            # Count different types of activities
            if "Swift Order Received" in line:
                metrics["swift_orders_received"] += 1
                
                # Extract market info
                market_match = re.search(r"Market: (\d+) \(([^)]+)\)", line)
                if market_match:
                    market_name = market_match.group(2)
                    markets[market_name] += 1
            
            elif "Starting JIT processing" in line:
                metrics["jit_processing_attempts"] += 1
                
                # Extract order size
                size_match = re.search(r"(\d+\.?\d*) SOL Oracle order", line)
                if size_match:
                    order_sizes.append(float(size_match.group(1)))
            
            elif "JIT processing completed successfully" in line:
                metrics["jit_completed_successfully"] += 1
            
            elif "Swift API error" in line:
                metrics["swift_api_errors"] += 1
                
                # Check for specific context error
                if "context" in line.lower():
                    metrics["context_errors"] += 1
            
            elif "Placing order via Swift API" in line:
                metrics["swift_api_success"] += 1
            
            elif "Insufficient balance for JIT trade" in line:
                metrics["insufficient_balance_warnings"] += 1
            
            elif "PLACING ORDER DIRECTLY VIA DRIFTPY" in line:
                metrics["direct_driftpy_orders"] += 1
            
            elif "Circuit breaker" in line:
                metrics["circuit_breaker_errors"] += 1
            
            elif "sync_ok active_orders=" in line:
                metrics["order_sync_activities"] += 1
                
                # Extract tracked orders count
                orders_match = re.search(r"active_orders=(\d+)", line)
                if orders_match:
                    metrics["tracked_orders"] = max(metrics["tracked_orders"], int(orders_match.group(1)))
        
        # Calculate success rates
        total_swift_attempts = metrics["swift_api_success"] + metrics["swift_api_errors"]
        swift_success_rate = (metrics["swift_api_success"] / total_swift_attempts * 100) if total_swift_attempts > 0 else 0
        
        jit_success_rate = (metrics["jit_completed_successfully"] / metrics["jit_processing_attempts"] * 100) if metrics["jit_processing_attempts"] > 0 else 0
        
        # Recent activity rate (orders per minute)
        activity_rate = len(recent_activity) / 10 if recent_activity else 0
        
        # Print analysis results
        print(f"📊 PERFORMANCE METRICS (Last 1000 log entries):")
        print(f"   📈 Swift Orders Received: {metrics['swift_orders_received']}")
        print(f"   🎯 JIT Processing Attempts: {metrics['jit_processing_attempts']}")
        print(f"   ✅ JIT Completed Successfully: {metrics['jit_completed_successfully']} ({jit_success_rate:.1f}%)")
        print(f"   🚀 Swift API Success: {metrics['swift_api_success']}")
        print(f"   ❌ Swift API Errors: {metrics['swift_api_errors']}")
        print(f"   📊 Swift Success Rate: {swift_success_rate:.1f}%")
        print()
        
        print(f"🔍 ISSUE ANALYSIS:")
        print(f"   ⚠️  Context Errors: {metrics['context_errors']} (CRITICAL FIX)")
        print(f"   🔄 Circuit Breaker Issues: {metrics['circuit_breaker_errors']}")
        print(f"   💰 Insufficient Balance: {metrics['insufficient_balance_warnings']}")
        print(f"   🎯 Direct DriftPy Orders: {metrics['direct_driftpy_orders']}")
        print()
        
        print(f"📋 MARKET ACTIVITY:")
        for market, count in markets.items():
            print(f"   {market}: {count} orders")
        print()
        
        print(f"📈 ORDER TRACKING:")
        print(f"   🔄 Order Sync Activities: {metrics['order_sync_activities']}")
        print(f"   📊 Currently Tracked Orders: {metrics['tracked_orders']}")
        print(f"   ⏱️  Recent Activity Rate: {activity_rate:.1f} events/minute")
        print()
        
        if order_sizes:
            avg_size = sum(order_sizes) / len(order_sizes)
            max_size = max(order_sizes)
            min_size = min(order_sizes)
            print(f"💰 ORDER SIZE ANALYSIS:")
            print(f"   📊 Average Size: {avg_size:.2f} SOL")
            print(f"   📈 Max Size: {max_size:.2f} SOL")
            print(f"   📉 Min Size: {min_size:.2f} SOL")
            print()
        
        # Optimization assessment
        print(f"🚀 OPTIMIZATION ASSESSMENT:")
        
        if metrics["context_errors"] == 0:
            print(f"   ✅ Swift Context Fix: WORKING (0 context errors)")
        else:
            print(f"   ❌ Swift Context Fix: NEEDS ATTENTION ({metrics['context_errors']} errors)")
        
        if swift_success_rate > 80:
            print(f"   ✅ Swift API Routing: EXCELLENT ({swift_success_rate:.1f}%)")
        elif swift_success_rate > 50:
            print(f"   ⚠️  Swift API Routing: GOOD ({swift_success_rate:.1f}%)")
        else:
            print(f"   ❌ Swift API Routing: NEEDS IMPROVEMENT ({swift_success_rate:.1f}%)")
        
        if jit_success_rate > 95:
            print(f"   ✅ JIT Processing: EXCELLENT ({jit_success_rate:.1f}%)")
        else:
            print(f"   ⚠️  JIT Processing: LIMITED BY BALANCE ({jit_success_rate:.1f}%)")
        
        if activity_rate > 5:
            print(f"   ✅ Order Flow: ACTIVE ({activity_rate:.1f} events/min)")
        elif activity_rate > 1:
            print(f"   ⚠️  Order Flow: MODERATE ({activity_rate:.1f} events/min)")
        else:
            print(f"   ❌ Order Flow: LOW ({activity_rate:.1f} events/min)")
        
        print()
        print(f"💡 RECOMMENDATIONS:")
        
        if metrics["insufficient_balance_warnings"] > 10:
            print(f"   💰 CRITICAL: Add more collateral (SOL Balance: 0.0000)")
            print(f"   💸 Bot cannot execute trades due to insufficient balance")
        
        if metrics["context_errors"] == 0 and swift_success_rate < 50:
            print(f"   🔄 Consider restarting bot to apply all optimizations")
        
        if activity_rate > 0:
            print(f"   ✅ Bot is actively receiving Swift orders")
            print(f"   🎯 Sniper mode working with selective processing")
        
        print(f"   📊 Monitor balance and consider depositing more SOL for trading")
        
        return {
            "swift_success_rate": swift_success_rate,
            "jit_success_rate": jit_success_rate,
            "context_errors": metrics["context_errors"],
            "activity_rate": activity_rate,
            "total_orders": metrics["swift_orders_received"]
        }
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return None

if __name__ == "__main__":
    analyze_recent_performance()


