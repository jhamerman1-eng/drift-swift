#!/usr/bin/env python3
"""
MM Bot Fix Verification Script
Tests if the JSON serialization fix worked by monitoring bot health
"""

import subprocess
import time
import sys
import os
from pathlib import Path

def run_verification():
    """Verify that the MM bot fix worked"""

    print("MM BOT FIX VERIFICATION")
    print("=" * 60)
    print()

    # 1. Check if bot can start without immediate crash
    print("1️⃣ TESTING BOT STARTUP...")
    try:
        # Start the bot with a timeout
        proc = subprocess.Popen([
            sys.executable, "run_mm_bot.py", "--env", "devnet", "--cfg", "configs/core/drift_client.yaml"
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd="drift-bots")

        print("✅ Bot process started successfully")

        # Monitor for first 30 seconds
        start_time = time.time()
        crash_detected = False
        order_count = 0

        while time.time() - start_time < 30:
            if proc.poll() is not None:
                # Process terminated
                crash_detected = True
                break

            # Read output
            if proc.stdout:
                line = proc.stdout.readline()
                if line:
                    if "Order placed" in line or "order" in line.lower():
                        order_count += 1
                    if "JSON" in line and ("error" in line.lower() or "serializable" in line.lower()):
                        print(f"❌ JSON error detected: {line.strip()}")
                        crash_detected = True
                        break
                    if "Error" in line or "Exception" in line:
                        print(f"⚠️  Error detected: {line.strip()}")

            time.sleep(0.1)

        if crash_detected:
            print("❌ Bot crashed within 30 seconds")
            if proc.stdout:
                remaining = proc.stdout.read()
                if remaining:
                    print("Last output:")
                    print(remaining[-500:])  # Last 500 chars
        else:
            print("✅ Bot survived first 30 seconds")
            print(f"📊 Orders detected: {order_count}")

        # Clean up
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
                print("✅ Bot terminated cleanly")
            except subprocess.TimeoutExpired:
                proc.kill()
                print("⚠️  Bot had to be force-killed")

    except Exception as e:
        print(f"❌ Failed to start bot: {e}")

    print()

    # 2. Check log files for patterns
    print("2️⃣ ANALYZING LOG FILES...")
    log_file = Path("mm_bot.log")
    if log_file.exists():
        with open(log_file, 'r') as f:
            content = f.read()

        # Analyze content
        lines = content.split('\n')
        duration = 0
        if len(lines) > 1:
            # Try to extract timestamps
            import re
            timestamps = []
            for line in lines:
                match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if match:
                    timestamps.append(match.group(1))

            if len(timestamps) > 1:
                from datetime import datetime
                first_time = datetime.strptime(timestamps[0], '%Y-%m-%d %H:%M:%S')
                last_time = datetime.strptime(timestamps[-1], '%Y-%m-%d %H:%M:%S')
                duration = (last_time - first_time).total_seconds()
                print(".1f")

        # Check for errors
        json_errors = [line for line in lines if "JSON" in line and ("error" in line.lower() or "serializable" in line.lower())]
        order_lines = [line for line in lines if "Order" in line or "order" in line.lower()]
        error_lines = [line for line in lines if "Error" in line or "Exception" in line]

        print(f"📊 JSON errors: {len(json_errors)}")
        print(f"📊 Order mentions: {len(order_lines)}")
        print(f"📊 General errors: {len(error_lines)}")

        if json_errors:
            print("❌ Recent JSON errors:")
            for error in json_errors[-3:]:
                print(f"   {error.strip()}")

        if duration > 60:
            print("✅ Bot ran for more than 1 minute - good sign!")
        elif duration > 17:
            print("⚠️  Bot ran longer than 17 seconds but less than 1 minute")
        else:
            print("❌ Bot ran for less than 17 seconds - still broken")

    else:
        print("⚠️  No mm_bot.log file found")

    print()

    # 3. Summary
    print("3️⃣ VERIFICATION SUMMARY")
    print("-" * 30)

    if duration > 60 and json_errors == 0:
        print("🎉 SUCCESS: Bot appears to be working!")
        print("   ✅ Runs for > 1 minute")
        print("   ✅ No JSON serialization errors")
        print("   ✅ Continuous operation achieved")
    elif duration > 17 and len(json_errors) < len(lines) * 0.1:  # Less than 10% errors
        print("⚠️  PARTIAL SUCCESS: Bot improved but still has issues")
        print("   ✅ Runs longer than 17 seconds")
        print("   ⚠️  Some JSON errors remain")
    else:
        print("❌ FAILED: Bot still broken")
        print("   ❌ Still crashes quickly or has JSON errors")

    print()
    print("💡 Next steps:")
    print("   1. Check the specific error messages")
    print("   2. Look at line 466 in your code")
    print("   3. Consider alternative serialization approach")
    print("   4. Test with simpler payload first")

if __name__ == "__main__":
    run_verification()

