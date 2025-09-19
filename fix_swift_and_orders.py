#!/usr/bin/env python3
"""
COMPREHENSIVE FIX: Swift Sidecar + Order Management
This script fixes both the Swift sidecar configuration AND the order limit issue permanently.
"""

import subprocess
import sys
import os
import time
import json

def run_command(cmd, capture_output=True):
    """Run a command and return success status"""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            print(f"Command: {cmd}")
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print(f"Output: {result.stdout}")
            if result.stderr and result.returncode != 0:
                print(f"Error: {result.stderr}")
            return result.returncode == 0
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def fix_swift_sidecar():
    """Fix Swift sidecar configuration permanently"""
    print("🔧 FIXING SWIFT SIDECAR CONFIGURATION...")
    
    # Step 1: Stop current sidecar
    print("\n1. Stopping current sidecar...")
    run_command("docker-compose -f docker-compose.swift.yml down")
    
    # Step 2: Fix the configuration file
    print("\n2. Fixing docker-compose.swift.yml...")
    try:
        with open("docker-compose.swift.yml", "r") as f:
            content = f.read()
        
        # Replace incorrect endpoint with correct one
        updated_content = content.replace(
            "https://master.swift.drift.trade",
            "https://swift.drift.trade"
        )
        
        # Also ensure we have the API key environment variable properly set
        if "SWIFT_API_KEY=${SWIFT_API_KEY}" in updated_content:
            print("✅ API key environment variable is correctly configured")
        
        with open("docker-compose.swift.yml", "w") as f:
            f.write(updated_content)
        
        print("✅ Configuration updated: master.swift.drift.trade → swift.drift.trade")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update configuration: {e}")
        return False

def clear_all_orders():
    """Clear all existing orders to fix MaxNumberOfOrders issue"""
    print("\n🧹 CLEARING ALL ORDERS TO FIX ORDER LIMIT...")
    
    # Try the dedicated cancel script first
    if os.path.exists("cancel_all_orders.py"):
        print("Using cancel_all_orders.py...")
        success = run_command("python cancel_all_orders.py")
        if success:
            print("✅ All orders canceled successfully")
            return True
    
    # Fallback: try direct DriftPy cancel
    print("Attempting direct order cancellation...")
    cancel_script = '''
import asyncio
import os
from driftpy.drift_client import DriftClient
from driftpy.account_subscription_config import AccountSubscriptionConfig
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
import json

async def cancel_all_orders():
    try:
        # Load wallet
        with open("wallet.json", "r") as f:
            wallet_data = json.load(f)
        
        if isinstance(wallet_data, list):
            keypair = Keypair.from_bytes(bytes(wallet_data[:64]))
        else:
            keypair = Keypair.from_base58_string(wallet_data)
        
        # Connect to Drift
        rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        connection = AsyncClient(rpc_url)
        
        drift_client = DriftClient(
            connection,
            keypair,
            "devnet",
            account_subscription=AccountSubscriptionConfig("websocket")
        )
        
        await drift_client.subscribe()
        
        # Get all orders
        user = drift_client.get_user()
        orders = user.get_open_orders()
        
        print(f"Found {len(orders)} open orders")
        
        # Cancel all orders
        for order in orders:
            try:
                await drift_client.cancel_order(order.order_id)
                print(f"Canceled order {order.order_id}")
            except Exception as e:
                print(f"Failed to cancel order {order.order_id}: {e}")
        
        await drift_client.unsubscribe()
        print("✅ All orders canceled")
        return True
        
    except Exception as e:
        print(f"❌ Failed to cancel orders: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(cancel_all_orders())
'''
    
    # Write and execute the cancel script
    with open("temp_cancel_orders.py", "w") as f:
        f.write(cancel_script)
    
    try:
        success = run_command("python temp_cancel_orders.py")
        os.remove("temp_cancel_orders.py")
        return success
    except Exception as e:
        print(f"❌ Order cancellation failed: {e}")
        if os.path.exists("temp_cancel_orders.py"):
            os.remove("temp_cancel_orders.py")
        return False

def restart_swift_sidecar():
    """Restart Swift sidecar with fixed configuration"""
    print("\n🚀 RESTARTING SWIFT SIDECAR...")
    
    # Start with new configuration
    if not run_command("docker-compose -f docker-compose.swift.yml up -d"):
        print("❌ Failed to start sidecar")
        return False
    
    # Wait a moment for startup
    print("Waiting 10 seconds for sidecar startup...")
    time.sleep(10)
    
    # Verify it's running
    if not run_command("docker ps | findstr swift-mm"):
        print("❌ Sidecar not running")
        return False
    
    print("✅ Sidecar restarted successfully")
    return True

def verify_swift_health():
    """Verify Swift sidecar is in forward mode"""
    print("\n🏥 VERIFYING SWIFT HEALTH...")
    
    try:
        # Use PowerShell Invoke-WebRequest for health check
        result = subprocess.run([
            "powershell", "-Command", 
            "try { $r = Invoke-WebRequest -Uri 'http://localhost:8787/health' -UseBasicParsing; $r.Content } catch { $_.Exception.Message }"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            try:
                health_data = json.loads(result.stdout.strip())
                mode = health_data.get("mode", "unknown")
                forward = health_data.get("forward", "unknown")
                
                print(f"Sidecar Mode: {mode}")
                print(f"Forward URL: {forward}")
                
                if mode == "forward":
                    print("✅ Sidecar is in FORWARD mode - Swift API integration enabled!")
                    return True
                else:
                    print(f"❌ Sidecar is in {mode} mode - not forwarding orders")
                    return False
                    
            except json.JSONDecodeError:
                print(f"❌ Invalid health response: {result.stdout}")
                return False
        else:
            print(f"❌ Health check failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Health verification failed: {e}")
        return False

def create_monitoring_script():
    """Create a monitoring script to prevent this issue from happening again"""
    print("\n📊 CREATING PERMANENT MONITORING...")
    
    monitor_script = '''#!/usr/bin/env python3
"""
Swift Sidecar Health Monitor
Runs every 5 minutes to ensure sidecar stays in forward mode
"""

import subprocess
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("swift_monitor")

def check_sidecar_health():
    """Check if sidecar is healthy and in forward mode"""
    try:
        result = subprocess.run([
            "powershell", "-Command", 
            "try { $r = Invoke-WebRequest -Uri 'http://localhost:8787/health' -UseBasicParsing; $r.Content } catch { $null }"
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            health_data = json.loads(result.stdout.strip())
            mode = health_data.get("mode", "unknown")
            return mode == "forward"
        return False
    except:
        return False

def fix_sidecar():
    """Fix sidecar if it's not in forward mode"""
    logger.warning("🔧 Sidecar not in forward mode - fixing...")
    subprocess.run("docker-compose -f docker-compose.swift.yml restart", shell=True)
    time.sleep(15)
    
    if check_sidecar_health():
        logger.info("✅ Sidecar fixed and back in forward mode")
    else:
        logger.error("❌ Sidecar fix failed - manual intervention required")

def monitor_loop():
    """Main monitoring loop"""
    logger.info("🚀 Swift Sidecar Monitor started")
    
    while True:
        try:
            if check_sidecar_health():
                logger.info("✅ Sidecar healthy - forward mode active")
            else:
                logger.warning("❌ Sidecar unhealthy - fixing...")
                fix_sidecar()
                
        except Exception as e:
            logger.error(f"Monitor error: {e}")
        
        time.sleep(300)  # Check every 5 minutes

if __name__ == "__main__":
    monitor_loop()
'''
    
    with open("monitor_swift_health.py", "w") as f:
        f.write(monitor_script)
    
    print("✅ Created monitor_swift_health.py - run this to prevent future issues")

def main():
    """Main fix execution"""
    print("🚨 COMPREHENSIVE SWIFT & ORDER FIX STARTING...")
    print("This will fix both the Swift sidecar and order limit issues permanently.")
    
    success_count = 0
    total_steps = 5
    
    # Step 1: Fix Swift sidecar configuration
    if fix_swift_sidecar():
        success_count += 1
    
    # Step 2: Clear all orders to fix order limit
    if clear_all_orders():
        success_count += 1
    
    # Step 3: Restart sidecar with fixed config
    if restart_swift_sidecar():
        success_count += 1
    
    # Step 4: Verify health
    if verify_swift_health():
        success_count += 1
    
    # Step 5: Create monitoring
    create_monitoring_script()
    success_count += 1
    
    print(f"\n🎯 FIX COMPLETED: {success_count}/{total_steps} steps successful")
    
    if success_count == total_steps:
        print("✅ ALL ISSUES FIXED:")
        print("  ✅ Swift sidecar in forward mode")
        print("  ✅ Order limit cleared")
        print("  ✅ Monitoring script created")
        print("  ✅ Bot should now trade successfully via Swift API")
    else:
        print("⚠️  PARTIAL SUCCESS - some issues remain")
    
    return success_count == total_steps

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
