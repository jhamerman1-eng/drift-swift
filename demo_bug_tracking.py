#!/usr/bin/env python3
"""
Demonstration of Enhanced Bug Tracking System
Shows how bugs are automatically logged, tracked, and resolved
"""

import sys
import time
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))

from logging_config import setup_critical_logging, get_bug_tracker, log_error_with_tracking

def demo_bug_tracking():
    """Demonstrate the bug tracking system"""

    # Setup logging
    logger = setup_critical_logging("demo-bug-tracker")
    bug_tracker = get_bug_tracker("demo-bug-tracker")

    print("🐛 ENHANCED BUG TRACKING SYSTEM DEMONSTRATION")
    print("=" * 60)

    # 1. Log a manual bug
    print("\n1. Logging a manual bug...")
    bug_id = bug_tracker.log_bug(
        bug_id="DEMO-001",
        description="Wallet connection timeout during high load",
        root_cause="RPC endpoint rate limiting",
        impact="Bot cannot place orders during peak trading hours",
        priority="high",
        context={
            "affected_component": "wallet_manager",
            "rpc_endpoints": ["endpoint1", "endpoint2"],
            "timeout_threshold": "30s"
        }
    )
    print(f"✅ Bug logged with ID: {bug_id}")

    # 2. Simulate error with automatic bug tracking
    print("\n2. Simulating error with automatic bug tracking...")
    try:
        # Simulate an error
        raise ConnectionError("RPC endpoint rate limit exceeded")
    except Exception as e:
        bug_id_2 = log_error_with_tracking(logger, e, {
            "component": "rpc_client",
            "operation": "get_recent_blockhash",
            "endpoint": "https://api.mainnet-beta.solana.com"
        })
        print(f"✅ Error automatically tracked with bug ID: {bug_id_2}")

    # 3. Log resolution attempt
    print("\n3. Logging bug resolution attempt...")
    bug_tracker.log_bug_resolution_attempt(
        bug_id=bug_id,
        solution_attempted="Implemented exponential backoff with jitter",
        success=True,
        notes="Added retry logic with 1s, 2s, 4s, 8s delays. Reduced timeout failures by 85%."
    )

    # 4. Log failed resolution attempt
    print("\n4. Logging failed resolution attempt...")
    bug_tracker.log_bug_resolution_attempt(
        bug_id=bug_id_2,
        solution_attempted="Increased timeout from 30s to 60s",
        success=False,
        notes="Timeout increase helped but still seeing failures during extreme load."
    )

    # 5. Get bug summary
    print("\n5. Getting bug summary...")
    summary = bug_tracker.get_bug_summary()
    print(f"📊 Active bugs: {summary['total_active']}")
    print(f"🔴 Critical: {summary['by_priority']['critical']}")
    print(f"🟠 High: {summary['by_priority']['high']}")
    print(f"🟡 Medium: {summary['by_priority']['medium']}")
    print(f"🟢 Low: {summary['by_priority']['low']}")

    print("\n6. Recent bug activity:")
    for bug_id, timestamp in summary['recent_activity']:
        print(f"   • {bug_id}: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}")

    print("\n" + "=" * 60)
    print("✅ DEMONSTRATION COMPLETE")
    print("\n📋 Key Features Demonstrated:")
    print("   • Automatic bug detection and logging")
    print("   • Comprehensive context capture")
    print("   • Resolution tracking with success/failure")
    print("   • Priority-based bug management")
    print("   • Persistent bug registry")
    print("   • Integration with existing logging system")

    print("\n📁 Check logs/demo-bug-tracker.log for detailed logs")
    print("📁 Check logs/bug_registry_active.json for bug registry")

if __name__ == "__main__":
    demo_bug_tracking()
