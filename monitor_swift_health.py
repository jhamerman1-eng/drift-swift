#!/usr/bin/env python3
"""
Swift API Health Monitor
Monitors Swift API connectivity and prevents regressions
"""

import asyncio
import json
import time
import httpx
from datetime import datetime

async def check_swift_health():
    """Check Swift API and sidecar health"""
    print(f"🏥 Swift Health Check - {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 50)
    
    issues = []
    
    # Check sidecar health
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8787/health", timeout=3.0)
            health = response.json()
            
            print(f"🔧 Sidecar Status: {response.status_code}")
            print(f"🔧 Mode: {health.get('mode', 'unknown')}")
            print(f"🔧 Forward URL: {health.get('forward', 'none')}")
            
            # Check mode
            if health.get('mode') != 'forward':
                issues.append(f"❌ Sidecar not in forward mode: {health.get('mode')}")
            else:
                print("✅ Sidecar in forward mode")
            
            # Check upstream
            upstream = health.get('upstream', {})
            if upstream.get('ok'):
                response_time = upstream.get('response_time_ms', 0)
                print(f"✅ Swift API connected: {response_time}ms")
                
                if response_time > 2000:
                    issues.append(f"⚠️  High Swift API latency: {response_time}ms")
                    
            else:
                issues.append("❌ Swift API not connected")
                
            # Check forward URL
            expected_url = "https://master.swift.drift.trade"
            if health.get('forward') != expected_url:
                issues.append(f"❌ Wrong forward URL: {health.get('forward')} (expected {expected_url})")
            else:
                print("✅ Correct Swift API endpoint")
                
    except Exception as e:
        issues.append(f"❌ Sidecar unreachable: {e}")
    
    # Check direct Swift API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://master.swift.drift.trade/health", timeout=3.0)
            if response.status_code == 200:
                print("✅ Direct Swift API reachable")
            else:
                issues.append(f"⚠️  Swift API response: {response.status_code}")
                
    except Exception as e:
        issues.append(f"❌ Direct Swift API unreachable: {e}")
    
    # Summary
    print("-" * 50)
    if not issues:
        print("🎉 ALL SYSTEMS HEALTHY!")
        print("✅ Ready for Swift API trading")
        return True
    else:
        print("⚠️  ISSUES DETECTED:")
        for issue in issues:
            print(f"   {issue}")
        return False

def check_envelope_fields():
    """Verify envelope still has correct field names"""
    print("\n🔍 Envelope Field Check")
    print("-" * 30)
    
    # Import envelope creator
    try:
        from libs.drift.swift_envelope import SwiftEnvelopeCreator
        
        # Check that the class has the right validation method
        envelope_creator = SwiftEnvelopeCreator()
        
        # Test envelope format
        test_envelope = {
            "market_index": 0,
            "market_type": "perp",
            "message": "deadbeef",
            "signature": "dGVzdA==", 
            "taker_authority": "test_taker",
            "signing_authority": "test_signer"
        }
        
        validation = envelope_creator._validate_envelope(test_envelope)
        
        if validation["valid"]:
            print("✅ Envelope validation works")
            print("✅ Required fields: message, signature, taker_authority, signing_authority")
            return True
        else:
            print(f"❌ Envelope validation failed: {validation['errors']}")
            return False
            
    except Exception as e:
        print(f"❌ Envelope check failed: {e}")
        return False

def check_driver_mapping():
    """Verify driver still maps fields correctly"""
    print("\n🔧 Driver Mapping Check") 
    print("-" * 30)
    
    try:
        from libs.drift.drivers.swift import SwiftSidecarDriver
        
        # Simple test
        test_envelope = {
            "message": "test_message",
            "signature": "test_sig",
            "taker_authority": "test_taker", 
            "signing_authority": "test_signer",
            "market_index": 0,
            "market_type": "perp"
        }
        
        # Test basic driver functionality
        driver = SwiftSidecarDriver.__new__(SwiftSidecarDriver)
        driver.base_url = "http://localhost:8787"
        
        payload = driver._create_swift_payload(test_envelope)
        
        required_keys = ["message", "signature", "taker_authority", "signing_authority"]
        for key in required_keys:
            if key not in payload:
                print(f"❌ Missing key in payload: {key}")
                return False
                
        print("✅ Driver mapping works")
        print("✅ All required fields mapped correctly")
        return True
        
    except Exception as e:
        print(f"❌ Driver check failed: {e}")
        return False

async def main():
    """Run comprehensive health check"""
    print("🎯 Swift API Health Monitor")
    print("=" * 60)
    
    results = []
    
    # Check Swift connectivity
    results.append(await check_swift_health())
    
    # Check envelope format
    results.append(check_envelope_fields())
    
    # Check driver mapping
    results.append(check_driver_mapping())
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 HEALTH CHECK PASSED ({passed}/{total})")
        print("\n🚀 Swift API is ready for trading!")
        print("   • Sidecar connected to Swift API")
        print("   • Envelope format correct")
        print("   • Driver mapping works")
        print("\n💡 Run this script periodically to monitor health")
        return True
    else:
        print(f"⚠️  HEALTH CHECK ISSUES ({passed}/{total})")
        print("\n🔧 Some components need attention")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
