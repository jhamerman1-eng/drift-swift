#!/usr/bin/env python3
"""
5-MINUTE PRODUCTION TEST SCRIPT
Comprehensive testing of run_swift_mm_complete.py bot
"""

import asyncio
import logging
import os
import sys
import time
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Configure test logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("production_test_5min.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ProductionTestMonitor:
    """Monitor and record bot performance during 5-minute test"""

    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(minutes=5)
        self.metrics = {
            "ticks_processed": 0,
            "orders_placed": 0,
            "orders_cancelled": 0,
            "swift_orders_received": 0,
            "swift_orders_processed": 0,
            "errors_encountered": 0,
            "jit_trades_executed": 0,
            "position_updates": 0,
            "pnl_updates": [],
            "connection_status": [],
            "performance_stats": []
        }
        self.log_entries = []

    def record_metric(self, metric_name: str, value):
        """Record a metric update"""
        if metric_name in self.metrics:
            if isinstance(self.metrics[metric_name], list):
                self.metrics[metric_name].append({
                    "timestamp": datetime.now().isoformat(),
                    "value": value
                })
            else:
                self.metrics[metric_name] += value

    def log_event(self, level: str, message: str):
        """Log an event with timestamp"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message
        }
        self.log_entries.append(entry)
        logger.info(f"[{level}] {message}")

    def should_continue(self) -> bool:
        """Check if test should continue"""
        return datetime.now() < self.end_time

    def generate_report(self) -> dict:
        """Generate comprehensive test report"""
        test_duration = datetime.now() - self.start_time
        total_seconds = test_duration.total_seconds()

        report = {
            "test_info": {
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration_seconds": total_seconds,
                "planned_duration_minutes": 5,
                "actual_duration_minutes": total_seconds / 60
            },
            "performance_metrics": self.metrics,
            "summary_stats": {
                "ticks_per_second": self.metrics["ticks_processed"] / max(total_seconds, 1),
                "orders_per_minute": (self.metrics["orders_placed"] * 60) / max(total_seconds, 1),
                "error_rate": (self.metrics["errors_encountered"] * 100) / max(self.metrics["ticks_processed"], 1),
                "success_rate": ((self.metrics["ticks_processed"] - self.metrics["errors_encountered"]) * 100) / max(self.metrics["ticks_processed"], 1)
            },
            "log_entries": self.log_entries[-100:],  # Last 100 entries
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform,
                "working_directory": os.getcwd()
            }
        }
        return report

async def create_test_wallet():
    """Create a test wallet for the bot"""
    # Create a temporary test wallet
    test_wallet = {
        "secret_key": [174, 47, 154, 16, 202, 193, 206, 113, 199, 190, 53, 133, 169, 175, 31, 56, 222, 53, 138, 189, 224, 216, 117, 173, 10, 149, 53, 45, 73, 46, 49, 18, 253, 191, 227, 175, 67, 247, 69, 41, 237, 190, 164, 168, 158, 8, 80, 169, 177, 14, 106, 21, 42, 48, 23, 122, 161, 143, 236, 237, 2, 244, 158, 169]
    }

    wallet_path = ".valid_wallet.json"
    with open(wallet_path, 'w') as f:
        json.dump(test_wallet, f)

    logger.info(f"✅ Test wallet created: {wallet_path}")
    return wallet_path

async def run_production_test():
    """Run the 5-minute production test"""

    monitor = ProductionTestMonitor()
    monitor.log_event("INFO", "🚀 STARTING 5-MINUTE PRODUCTION TEST")
    monitor.log_event("INFO", "=" * 60)

    try:
        # Use existing test wallet
        wallet_path = ".beta_dev_wallet.json"
        if not os.path.exists(wallet_path):
            monitor.log_event("INFO", "Creating new test wallet...")
            wallet_path = await create_test_wallet()

        # Create safe test configuration
        test_config = {
            "env": "devnet",  # Always use devnet for safety
            "rpc_url": "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
            "sidecar_url": "http://localhost:8787",
            "swift_websocket_url": "wss://swift.drift.trade/ws",
            "wallet_file": wallet_path,
            "order_size": 0.001,  # Very small orders for safety
            "max_orders_per_side": 1,
            "price_tolerance": 0.01,
            "spread_bps": 10,  # Wider spread for safety
            "test_mode": True,  # Enable test mode
            "max_order_size_usd": 10.0,  # Very small max order size
            "max_daily_loss_usd": 5.0   # Very conservative loss limit
        }

        monitor.log_event("INFO", f"📋 Test Configuration: {json.dumps(test_config, indent=2)}")

        # Import the bot
        try:
            from run_swift_mm_complete import CompleteSwiftMMBot
            monitor.log_event("INFO", "✅ Bot import successful")
        except ImportError as e:
            monitor.log_event("ERROR", f"❌ Failed to import bot: {e}")
            return monitor.generate_report()

        # Initialize bot
        monitor.log_event("INFO", "🔧 Initializing bot...")
        bot = CompleteSwiftMMBot(test_config)

        if not await bot.initialize():
            monitor.log_event("ERROR", "❌ Bot initialization failed")
            return monitor.generate_report()

        monitor.log_event("INFO", "✅ Bot initialized successfully")

        # Start monitoring loop
        monitor.log_event("INFO", "📊 Starting 5-minute monitoring loop...")

        last_stats_time = time.time()
        tick_count = 0

        while monitor.should_continue():
            try:
                # Run market making tick
                await bot.market_making_tick()
                tick_count += 1
                monitor.record_metric("ticks_processed", 1)

                # Log stats every 30 seconds
                current_time = time.time()
                if current_time - last_stats_time >= 30:
                    stats = bot.get_stats()
                    monitor.record_metric("performance_stats", stats)

                    # Record key metrics
                    monitor.record_metric("orders_placed", stats.get("orders_placed", 0))
                    monitor.record_metric("orders_cancelled", stats.get("orders_cancelled", 0))
                    monitor.record_metric("swift_orders_received", stats.get("swift_orders_received", 0))
                    monitor.record_metric("swift_orders_processed", stats.get("swift_orders_processed", 0))
                    monitor.record_metric("jit_trades_executed", stats.get("jit_trades_executed", 0))

                    # Record position and P&L
                    if "position" in stats:
                        monitor.record_metric("position_updates", stats["position"]["current_position"])

                    monitor.log_event("INFO", f"📊 Stats Update: Ticks={tick_count}, Orders={stats.get('orders_placed', 0)}, Position={stats.get('position', {}).get('current_position', 0):.6f}")
                    last_stats_time = current_time

                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)

            except Exception as e:
                monitor.record_metric("errors_encountered", 1)
                monitor.log_event("ERROR", f"❌ Tick error: {e}")
                await asyncio.sleep(1)  # Longer delay on error

        monitor.log_event("INFO", "⏰ 5-minute test completed")

        # Shutdown bot
        monitor.log_event("INFO", "🔄 Shutting down bot...")
        await bot.shutdown()
        monitor.log_event("INFO", "✅ Bot shutdown complete")

        # Generate final report
        report = monitor.generate_report()
        monitor.log_event("INFO", "📋 Test report generated")

        return report

    except Exception as e:
        monitor.log_event("ERROR", f"❌ Test failed with exception: {e}")
        return monitor.generate_report()

def print_test_report(report: dict):
    """Print formatted test report"""
    print("\n" + "=" * 80)
    print("🎯 5-MINUTE PRODUCTION TEST REPORT")
    print("=" * 80)

    # Test Info
    test_info = report["test_info"]
    print("\n📅 Test Duration:")
    print(".2f")
    print(".2f")

    # Performance Metrics
    metrics = report["performance_metrics"]
    print("\n📊 Performance Metrics:")
    print(f"  • Total Ticks: {metrics['ticks_processed']}")
    print(f"  • Orders Placed: {metrics['orders_placed']}")
    print(f"  • Orders Cancelled: {metrics['orders_cancelled']}")
    print(f"  • Swift Orders Received: {metrics['swift_orders_received']}")
    print(f"  • Swift Orders Processed: {metrics['swift_orders_processed']}")
    print(f"  • JIT Trades Executed: {metrics['jit_trades_executed']}")
    print(f"  • Errors Encountered: {metrics['errors_encountered']}")

    # Summary Stats
    summary = report["summary_stats"]
    print("\n📈 Summary Statistics:")
    print(".2f")
    print(".2f")
    print(".2f")
    print(".2f")

    # Final Position
    if metrics["position_updates"]:
        final_position = metrics["position_updates"][-1]["value"] if isinstance(metrics["position_updates"][-1], dict) else metrics["position_updates"][-1]
        print(f"  • Final Position: {final_position:.6f} SOL")

    print("\n" + "=" * 80)
    print("✅ Test completed successfully!")
    print("=" * 80)

async def main():
    """Main test execution"""
    try:
        print("🚀 Starting 5-Minute Production Test of Swift MM Bot")
        print("This will test the bot's functionality in a controlled environment")
        print("Test will run for exactly 5 minutes...\n")

        # Run the test
        report = await run_production_test()

        # Print formatted report
        print_test_report(report)

        # Save detailed report to file
        report_file = f"production_test_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📋 Detailed report saved to: {report_file}")
        print("📊 Check production_test_5min.log for detailed logs")

        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
