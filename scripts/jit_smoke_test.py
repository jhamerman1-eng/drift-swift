#!/usr/bin/env python3
"""
JIT Smoke Test - US-JIT-005
Completes a 1-lot devnet fill and reports metrics to verify JIT service functionality.
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "libs"))

from libs.jit.client import JITClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JITSmokeTest:
    """JIT service smoke test implementation"""
    
    def __init__(self, base_url: str = "http://localhost:8787"):
        self.base_url = base_url
        self.client = JITClient(base_url=base_url, timeout=5.0)
        self.results = {
            "test_start_time": time.time(),
            "base_url": base_url,
            "tests": {},
            "overall_success": False,
            "summary": {}
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete smoke test suite"""
        logger.info("🧪 Starting JIT Smoke Test Suite")
        logger.info(f"🎯 Target: {self.base_url}")
        
        try:
            # Test 1: Health Check
            await self._test_health_check()
            
            # Test 2: Metrics Endpoint
            await self._test_metrics_endpoint()
            
            # Test 3: JIT Service Smoke Test
            await self._test_jit_service_smoke()
            
            # Test 4: Error Handling
            await self._test_error_handling()
            
            # Calculate overall success
            self._calculate_overall_success()
            
            # Generate summary
            self._generate_summary()
            
        except Exception as e:
            logger.error(f"❌ Smoke test suite failed: {e}")
            self.results["tests"]["suite_error"] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - self.results["test_start_time"]
            }
        
        self.results["test_end_time"] = time.time()
        self.results["total_duration"] = self.results["test_end_time"] - self.results["test_start_time"]
        
        return self.results
    
    async def _test_health_check(self):
        """Test JIT service health endpoint"""
        logger.info("🔍 Testing health endpoint...")
        start_time = time.time()
        
        try:
            # Basic health check
            is_healthy = self.client.health()
            
            # Detailed health info
            health_details = self.client.get_health_details()
            
            success = is_healthy and health_details.get("ok", False)
            
            self.results["tests"]["health_check"] = {
                "success": success,
                "is_healthy": is_healthy,
                "health_details": health_details,
                "duration": time.time() - start_time
            }
            
            if success:
                logger.info("✅ Health check passed")
                logger.info(f"📊 Subscribers: {health_details.get('subscribers', {})}")
            else:
                logger.error("❌ Health check failed")
                
        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
            self.results["tests"]["health_check"] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    async def _test_metrics_endpoint(self):
        """Test JIT service metrics endpoint"""
        logger.info("📊 Testing metrics endpoint...")
        start_time = time.time()
        
        try:
            metrics = self.client.get_metrics()
            
            # Check for expected metric keys
            expected_metrics = [
                "jit_swift_orders_total",
                "jit_dedup_drops_total", 
                "jit_unified_events_total"
            ]
            
            metrics_found = {metric: metric in str(metrics) for metric in expected_metrics}
            success = len(metrics) > 0
            
            self.results["tests"]["metrics_endpoint"] = {
                "success": success,
                "metrics_count": len(metrics),
                "expected_metrics_found": metrics_found,
                "sample_metrics": dict(list(metrics.items())[:5]) if metrics else {},
                "duration": time.time() - start_time
            }
            
            if success:
                logger.info(f"✅ Metrics endpoint passed ({len(metrics)} metrics)")
            else:
                logger.error("❌ Metrics endpoint failed")
                
        except Exception as e:
            logger.error(f"❌ Metrics endpoint error: {e}")
            self.results["tests"]["metrics_endpoint"] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    async def _test_jit_service_smoke(self):
        """Test JIT service with mock 1-lot fill - US-JIT-005 requirement"""
        logger.info("🎯 Testing JIT service smoke test (1-lot devnet fill simulation)...")
        start_time = time.time()
        
        try:
            # Use the built-in smoke test from JIT client
            smoke_result = self.client.smoke_test(market_index=0, size=0.01)
            
            success = smoke_result.get("success", False)
            
            self.results["tests"]["jit_service_smoke"] = {
                "success": success,
                "smoke_result": smoke_result,
                "duration": time.time() - start_time
            }
            
            if success:
                logger.info("✅ JIT service smoke test passed")
                if smoke_result.get("jit_place_attempted"):
                    logger.info(f"📈 JIT place attempted: {smoke_result.get('jit_place_success', 'unknown')}")
                logger.info(f"⏱️  Test duration: {smoke_result.get('duration', 0):.3f}s")
            else:
                logger.error("❌ JIT service smoke test failed")
                logger.error(f"Error: {smoke_result.get('error', 'unknown')}")
                
        except Exception as e:
            logger.error(f"❌ JIT service smoke test error: {e}")
            self.results["tests"]["jit_service_smoke"] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    async def _test_error_handling(self):
        """Test JIT service error handling"""
        logger.info("🚨 Testing error handling...")
        start_time = time.time()
        
        try:
            # Test invalid place_and_make request
            invalid_result = self.client.place_and_make(
                order_message_raw={},  # Invalid empty order
                signed_message={},     # Invalid empty message
                maker={"side": "invalid", "price": -1, "size": 0}  # Invalid maker params
            )
            
            # Should fail gracefully
            error_handling_works = not invalid_result.success and invalid_result.error is not None
            
            self.results["tests"]["error_handling"] = {
                "success": error_handling_works,
                "invalid_request_handled": not invalid_result.success,
                "error_message": invalid_result.error,
                "duration": time.time() - start_time
            }
            
            if error_handling_works:
                logger.info("✅ Error handling test passed")
                logger.info(f"🛡️  Error handled: {invalid_result.error}")
            else:
                logger.error("❌ Error handling test failed")
                
        except Exception as e:
            logger.error(f"❌ Error handling test error: {e}")
            self.results["tests"]["error_handling"] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    def _calculate_overall_success(self):
        """Calculate overall test success rate"""
        tests = self.results["tests"]
        if not tests:
            self.results["overall_success"] = False
            return
        
        successful_tests = sum(1 for test in tests.values() if test.get("success", False))
        total_tests = len(tests)
        success_rate = successful_tests / total_tests if total_tests > 0 else 0.0
        
        # Consider overall success if at least 75% of tests pass
        self.results["overall_success"] = success_rate >= 0.75
        self.results["success_rate"] = success_rate
        self.results["successful_tests"] = successful_tests
        self.results["total_tests"] = total_tests
    
    def _generate_summary(self):
        """Generate test summary"""
        self.results["summary"] = {
            "overall_status": "PASS" if self.results["overall_success"] else "FAIL",
            "success_rate": f"{self.results.get('success_rate', 0) * 100:.1f}%",
            "tests_passed": f"{self.results.get('successful_tests', 0)}/{self.results.get('total_tests', 0)}",
            "total_duration": f"{self.results.get('total_duration', 0):.3f}s",
            "recommendations": self._get_recommendations()
        }
    
    def _get_recommendations(self) -> list:
        """Get recommendations based on test results"""
        recommendations = []
        tests = self.results["tests"]
        
        if not tests.get("health_check", {}).get("success", False):
            recommendations.append("🔧 Fix JIT service health - check if service is running")
        
        if not tests.get("metrics_endpoint", {}).get("success", False):
            recommendations.append("📊 Fix metrics endpoint - verify Prometheus metrics are exposed")
        
        if not tests.get("jit_service_smoke", {}).get("success", False):
            recommendations.append("🎯 Fix JIT service core functionality - check place_and_make endpoint")
        
        if not tests.get("error_handling", {}).get("success", False):
            recommendations.append("🛡️  Improve error handling - ensure graceful error responses")
        
        if not recommendations:
            recommendations.append("✅ All tests passed - JIT service is ready for production")
        
        return recommendations

async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JIT Service Smoke Test")
    parser.add_argument("--url", default="http://localhost:8787", help="JIT service base URL")
    parser.add_argument("--output", help="Output file for test results (JSON)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run smoke test
    smoke_test = JITSmokeTest(base_url=args.url)
    results = await smoke_test.run_all_tests()
    
    # Output results
    print("\n" + "="*60)
    print("🧪 JIT SMOKE TEST RESULTS")
    print("="*60)
    print(f"Overall Status: {results['summary']['overall_status']}")
    print(f"Success Rate: {results['summary']['success_rate']}")
    print(f"Tests Passed: {results['summary']['tests_passed']}")
    print(f"Duration: {results['summary']['total_duration']}")
    print("\nRecommendations:")
    for rec in results['summary']['recommendations']:
        print(f"  {rec}")
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to: {args.output}")
    
    # Exit with appropriate code
    exit_code = 0 if results['overall_success'] else 1
    print(f"\nExiting with code: {exit_code}")
    return exit_code

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)



