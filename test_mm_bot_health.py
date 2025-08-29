#!/usr/bin/env python3
"""
Complete MM Bot Health Test Suite
Run all verification tests in sequence
"""

import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n🔄 {description}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("✅ SUCCESS")
            if result.stdout:
                print("Output:", result.stdout[-500:])  # Last 500 chars
            return True
        else:
            print("❌ FAILED")
            if result.stderr:
                print("Error:", result.stderr[-500:])
            return False

    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT (60 seconds)")
        return False
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")
        return False

def main():
    """Run complete health test suite"""
    print("🩺 COMPLETE MM BOT HEALTH TEST SUITE")
    print("=" * 70)

    tests_passed = 0
    total_tests = 0

    # Test 1: Quick verification
    total_tests += 1
    if run_command("python verify_mm_bot_fix.py", "Running Quick Verification Test"):
        tests_passed += 1

    # Test 2: Check if bot can start and survive 30 seconds
    total_tests += 1
    print(f"\n🔄 Test 2: Bot Survival Test (30 seconds)")
    print("-" * 50)

    try:
        proc = subprocess.Popen([
            sys.executable, "drift-bots/run_mm_bot.py",
            "--env", "devnet",
            "--cfg", "configs/core/drift_client.yaml"
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=".")

        print("✅ Bot started, monitoring for 30 seconds...")

        start_time = time.time()
        json_errors = 0
        order_count = 0

        while time.time() - start_time < 30:
            if proc.poll() is not None:
                break

            if proc.stdout:
                line = proc.stdout.readline()
                if line:
                    if "JSON" in line and ("error" in line.lower() or "serializable" in line.lower()):
                        json_errors += 1
                        print(f"🚨 JSON Error: {line.strip()}")
                    if "Order" in line or "order" in line.lower():
                        order_count += 1

            time.sleep(0.1)

        # Check results
        if proc.poll() is None:
            print("✅ Bot survived 30 seconds!")
            print(f"📊 Orders detected: {order_count}")
            print(f"🚨 JSON errors: {json_errors}")

            if json_errors == 0:
                tests_passed += 1
                print("✅ No JSON errors - excellent!")
            else:
                print("⚠️  JSON errors detected")

            proc.terminate()
            try:
                proc.wait(timeout=5)
            except:
                proc.kill()

        else:
            print("❌ Bot crashed before 30 seconds")

    except Exception as e:
        print(f"💥 Test failed: {e}")

    # Test 3: Check log file analysis
    total_tests += 1
    log_file = Path("mm_bot.log")
    if log_file.exists():
        print("\n🔄 Test 3: Log File Analysis")
        print("-" * 50)

        with open(log_file, 'r') as f:
            content = f.read()

        lines = content.split('\n')
        json_errors = sum(1 for line in lines if "JSON" in line and ("error" in line.lower() or "serializable" in line.lower()))
        order_lines = sum(1 for line in lines if "Order" in line or "order" in line.lower())

        print(f"📊 Total log lines: {len(lines)}")
        print(f"📊 JSON errors: {json_errors}")
        print(f"📊 Order mentions: {order_lines}")

        if json_errors == 0 and order_lines > 0:
            tests_passed += 1
            print("✅ Clean log file with orders - good!")
        elif json_errors == 0:
            print("⚠️  No JSON errors but no orders detected")
        else:
            print("❌ JSON errors found in logs")

    else:
        print("\n⚠️  Test 3: Log file not found")
        print("-" * 50)

    # Summary
    print("\n" + "=" * 70)
    print("📋 HEALTH TEST SUMMARY")
    print("=" * 70)

    print(f"✅ Tests Passed: {tests_passed}/{total_tests}")
    print(f"📊 Success Rate: {(tests_passed/total_tests*100):.1f}%")

    if tests_passed == total_tests:
        print("🎉 ALL TESTS PASSED - Bot appears healthy!")
        print()
        print("💡 Next steps:")
        print("   1. Start continuous monitoring: python monitor_mm_bot.py")
        print("   2. Let bot run for several minutes")
        print("   3. Check for continuous order placement")
    elif tests_passed >= total_tests * 0.5:
        print("⚠️  PARTIAL SUCCESS - Bot improved but has issues")
        print("💡 Focus on fixing remaining JSON errors")
    else:
        print("❌ MAJOR ISSUES - Bot still broken")
        print("💡 Need to fix JSON serialization problem")

    print()
    print("🔍 For continuous monitoring:")
    print("   python monitor_mm_bot.py")
    print()
    print("📊 For detailed verification:")
    print("   python verify_mm_bot_fix.py")

if __name__ == "__main__":
    main()
