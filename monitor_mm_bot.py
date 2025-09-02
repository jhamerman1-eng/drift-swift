#!/usr/bin/env python3
"""
MM Bot Health Monitor
Continuously monitors the MM bot's health and reports status
"""

import time
import subprocess
import sys
from pathlib import Path
import re
from datetime import datetime

class MMBotMonitor:
    def __init__(self, log_file="mm_bot.log"):
        self.log_file = Path(log_file)
        self.last_position = 0
        self.start_time = datetime.now()
        self.order_count = 0
        self.error_count = 0
        self.json_errors = 0
        self.last_order_time = None

    def check_process_running(self):
        """Check if mm bot process is running"""
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe'],
                capture_output=True, text=True, timeout=5
            )
            return 'run_mm_bot.py' in result.stdout
        except:
            return False

    def analyze_log_line(self, line):
        """Analyze a single log line"""
        if "Order placed" in line or "order" in line.lower():
            self.order_count += 1
            self.last_order_time = datetime.now()

        if "JSON" in line and ("error" in line.lower() or "serializable" in line.lower()):
            self.json_errors += 1
            print(f"🚨 JSON ERROR: {line.strip()}")

        if "Error" in line or "Exception" in line:
            self.error_count += 1
            print(f"⚠️  ERROR: {line.strip()}")

    def monitor_log_file(self):
        """Monitor the log file for new entries"""
        if not self.log_file.exists():
            return

        try:
            with open(self.log_file, 'r') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()

                for line in new_lines:
                    self.analyze_log_line(line)

        except Exception as e:
            print(f"Error reading log file: {e}")

    def print_status(self):
        """Print current status"""
        runtime = datetime.now() - self.start_time
        minutes = runtime.total_seconds() / 60

        print("\r" + "=" * 70)
        print(f"🤖 MM BOT HEALTH MONITOR (Running for {minutes:.1f} minutes)")
        print("=" * 70)

        print(f"📊 Orders Placed: {self.order_count}")
        print(f"⚠️  Total Errors: {self.error_count}")
        print(f"🚨 JSON Errors: {self.json_errors}")

        if self.last_order_time:
            time_since_last_order = datetime.now() - self.last_order_time
            seconds_since_order = time_since_last_order.total_seconds()
            if seconds_since_order < 60:
                print(".1f"            else:
                print(f"⏰ Last Order: {seconds_since_order:.0f} seconds ago ⚠️")

        # Health assessment
        if minutes > 1 and self.json_errors == 0 and self.order_count > 0:
            print("🟢 STATUS: HEALTHY - Bot is actively trading!")
        elif minutes > 1 and self.json_errors == 0:
            print("🟡 STATUS: RUNNING - No JSON errors, but no orders detected")
        elif minutes > 0.5 and self.json_errors > 0:
            print("🔴 STATUS: CRITICAL - JSON errors detected")
        elif minutes < 0.5:
            print("🔵 STATUS: STARTING - Bot initializing...")
        else:
            print("🟠 STATUS: UNKNOWN - Monitoring...")

        print("=" * 70)

    def run_monitor(self):
        """Main monitoring loop"""
        print("🔍 Starting MM Bot Health Monitor...")
        print("Press Ctrl+C to stop monitoring")

        try:
            while True:
                # Check if bot is still running
                if not self.check_process_running():
                    print("\n❌ ALERT: MM Bot process not found!")
                    break

                # Monitor log file
                self.monitor_log_file()

                # Print status every 10 seconds
                if int(time.time()) % 10 == 0:
                    self.print_status()

                time.sleep(1)

        except KeyboardInterrupt:
            print("\n🛑 Monitor stopped by user")

        # Final status
        self.print_status()
        print("
📋 FINAL SUMMARY:"        print(f"   Total Runtime: {(datetime.now() - self.start_time).total_seconds() / 60:.1f} minutes")
        print(f"   Orders Placed: {self.order_count}")
        print(f"   Errors: {self.error_count}")
        print(f"   JSON Errors: {self.json_errors}")

        if self.order_count > 0 and self.json_errors == 0:
            print("🎉 SUCCESS: Bot appears to be working correctly!")
        else:
            print("❌ ISSUE: Bot has problems that need fixing")

def main():
    """Main entry point"""
    monitor = MMBotMonitor()

    # Check if log file exists
    if not monitor.log_file.exists():
        print(f"⚠️  Log file {monitor.log_file} not found")
        print("💡 Start the MM bot first to generate logs")
        return

    monitor.run_monitor()

if __name__ == "__main__":
    main()

